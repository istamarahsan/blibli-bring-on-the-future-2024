import { exit } from "process";
import { loadEnv } from "./env.js";
import { CybersnakeApiConfig, start } from "./cybersnakeApi.js";

const env = loadEnv();
if (!env.success) {
    console.error("Failed to load environment variables.")
    env.error.issues.forEach(err => console.error(err.path.join("."), err.message))
    exit(1)
}
const port = Number.parseInt(env.data.PORT)
const config: CybersnakeApiConfig = {
    port: port,
    publicAccessSecret: env.data.PUBLIC_ACCESS_SECRET,
    accessSecret: env.data.ACCESS_SECRET,
    postgresUrl: env.data.POSTGRES_URL,
}
start(config)