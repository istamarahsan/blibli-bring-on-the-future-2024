import { DateTime } from "luxon";
import { LeaderboardEntry } from "./leaderboard.js";
import { Result } from "../../util/result.js";

export interface LeaderboardData {
    addEntry(name: string, score: number, date_created: DateTime): Promise<Result<LeaderboardEntry>>
    getAllEntries(): Promise<Result<LeaderboardEntry[]>>
    deleteAllEntries(): Promise<Result<bigint>>
}