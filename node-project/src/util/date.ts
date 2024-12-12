import { DateTime } from "luxon";

export interface DateTimeProvider {
    now(): DateTime
}