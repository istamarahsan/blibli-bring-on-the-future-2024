import Koa from 'koa'
import Router from 'koa-router';
import { DateTimeProvider } from './util/date.js';
import { DateTime } from 'luxon';
import { LeaderboardService } from './lib/leaderboard/leaderboardService.js';
import { KyselyData } from './data/kysely.js';
import { Kysely, PostgresDialect } from 'kysely';
import { DB } from './data/db.js';
import postgres from 'pg';
const { Pool } = postgres;
import { koaBody } from 'koa-body';
import { z } from 'zod';
import { FeedbackService } from './lib/feedback/feedbackService.js';

export type CybersnakeApiConfig = {
    port: number,
    publicAccessSecret: string,
    accessSecret: string,
    postgresUrl: string
}

export function start(config: CybersnakeApiConfig) {
    const app = new Koa()
    const router = new Router()
    const dateTimeProvider: DateTimeProvider = {
        now() {
            return DateTime.now()
        },
    }

    const pool = new Pool({
        connectionString: config.postgresUrl,
    })

    var kysely = new Kysely<DB>({
        dialect: new PostgresDialect({
            pool: pool
        })
    })

    const db = new KyselyData(kysely)
    const leaderboardService = new LeaderboardService(db, dateTimeProvider)
    const feedbackService = new FeedbackService(kysely)

    const public_auth: Koa.Middleware = async (ctx, next) => {
        if (!(ctx.request.header['authorization']?.startsWith("Bearer") ?? false)
            || !(ctx.request.header['authorization']?.slice("Bearer".length + 1) === config.publicAccessSecret ?? false)) {
            ctx.status = 401
            ctx.body = 'Unauthorized'
            return
        }
        await next()
    }

    const protected_auth: Koa.Middleware = async (ctx, next) => {
        if (!(ctx.request.header['authorization']?.startsWith("Bearer") ?? false)
            || !(ctx.request.header['authorization']?.slice("Bearer".length + 1) === config.accessSecret ?? false)) {
            ctx.status = 401
            ctx.body = 'Unauthorized'
            return
        }
        await next()
    }

    app.use(async (ctx, next) => {
        console.log(`${ctx.method} ${ctx.url}`);
        await next();
    });

    app.use(async (ctx, next) => {
        await next();
        const rt = ctx.response.get('X-Response-Time');
        console.log(`${ctx.method} ${ctx.url} - ${rt}`);
    });

    app.use(async (ctx, next) => {
        const start = Date.now();
        await next();
        const ms = Date.now() - start;
        ctx.set('X-Response-Time', `${ms}ms`);
    });

    router.get('/healthcheck', async (ctx) => {
        ctx.status = 200
    })

    const leaderboardPostRequestSchema = z.object({
        name: z.string(),
        score: z.number().int(),
    })
    router.post('/leaderboard', koaBody(), public_auth, async (ctx) => {
        if (!(ctx.request.headers["content-type"] === "application/json")) {
            ctx.status = 400
            return
        }
        
        const parse = leaderboardPostRequestSchema.safeParse(ctx.request.body)
        if (!parse.success) {
            ctx.status = 400
            return
        }
        
        const result = await leaderboardService.addEntry(parse.data.name, parse.data.score)
        if (!result.ok) {
            switch (result.error.type) {
                case "DataAccessError":
                    ctx.status = 500
                    ctx.body = "Internal data service error."
                    break;
                case "NameTooLong":
                    ctx.status = 400
                    ctx.body = `Name can be up to ${result.error.maximumLength} letters.`
                    break;
            }
            return
        }

        ctx.status = 200
    })

    const leaderboardGetResponseSchema = z.object({
        page: z.number().int().default(0),
        pages: z.number().int().default(1),
        pageSize: z.number().int().default(1),
        data: z.array(
            z.object({
                name: z.string(),
                score: z.number().int(),
                date: z.string(),
            }))
    })
    router.get('/leaderboard', public_auth, async (ctx) => {
        const fetch = await leaderboardService.getAllEntries()
        if (!fetch.ok) {
            ctx.status = 500
            return
        }
        const parse = leaderboardGetResponseSchema.safeParse({
            page: 0,
            pages: 1,
            pageSize: fetch.value.length,
            data: fetch.value.map(entry => ({
                name: entry.name,
                score: entry.score,
                date: entry.creationDate.toISO()
            }))
        })
        if (!parse.success) {
            ctx.status = 500
            return
        }
        ctx.status = 200
        ctx.body = JSON.stringify(parse.data)
    })

    router.delete('/leaderboard', protected_auth, async (ctx) => {
        const result = await leaderboardService.clearAllEntries()
        ctx.status = result.ok ? 200 : 500
    })

    router.get('/feedback', public_auth, async (ctx) => {
        const formUrl = await feedbackService.getFeedbackFormUrl()
        if (formUrl == undefined) {
            ctx.status = 404
            ctx.body = "Feedback data not found"
            return
        }
        ctx.status = 200
        ctx.body = JSON.stringify({
            formUrl: formUrl
        })
    })

    app.use(router.routes())

    const port = Math.floor(config.port)
    app.listen(port)
    console.log(`Listening on port ${port}`)
}