import { Result, error, ok } from "../../util/result.js";
import { LeaderboardEntry } from "./leaderboard.js";
import { LeaderboardData } from "./leaderboardData.js";
import { DateTimeProvider } from "../../util/date.js";

type DataAccessError = {
    type: "DataAccessError"
}

type NameTooLong = {
    type: "NameTooLong"
    maximumLength: number
}

export type AddEntryError = DataAccessError | NameTooLong

export class LeaderboardService {
    private readonly data: LeaderboardData
    private readonly dateTimeProvider: DateTimeProvider
    private readonly maxNameLength = 3
    constructor(data: LeaderboardData, dateTimeProvider: DateTimeProvider) {
        this.data = data;
        this.dateTimeProvider = dateTimeProvider;
    }
    async addEntry(name: string, score: number): Promise<Result<LeaderboardEntry, AddEntryError>> {
        if (name.length > this.maxNameLength) {
            return error({
                type: "NameTooLong",
                maximumLength: this.maxNameLength
            })
        }
        const now = this.dateTimeProvider.now();
        const addEntryResult = await this.data.addEntry(name, score, now);
        if (!addEntryResult.ok) {
            return error({
                type: "DataAccessError"
            })
        }
        return ok(addEntryResult.value)
    }
    async getAllEntries(): Promise<Result<LeaderboardEntry[]>> {
        return await this.data.getAllEntries();
    }
    async clearAllEntries(): Promise<Result<undefined>> {
        const deleteResult = await this.data.deleteAllEntries();
        return deleteResult.ok ? ok(undefined) : error(undefined);
    }
}