import { Kysely } from "kysely";
import { DB } from "../../data/db";

export class FeedbackService {
    private readonly db: Kysely<DB>
    constructor(db: Kysely<DB>) {
        this.db = db
    }
    async getFeedbackFormUrl(): Promise<string | undefined> {
        try {
            var firstRow = await this.db
            .selectFrom("feedbacklink")
            .selectAll()
            .limit(1)
            .executeTakeFirst()
            if (firstRow == undefined) {
                return undefined
            }
            return firstRow.link
        } catch (_) {
            return undefined
        }
        
    }
}
