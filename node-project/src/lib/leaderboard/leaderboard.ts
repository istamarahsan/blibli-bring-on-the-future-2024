import { DateTime } from "luxon"

export type LeaderboardEntry = {
    name: string,
    score: number,
    creationDate: DateTime
}