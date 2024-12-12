export interface Leaderboard {
  name: string;
  score: number;
  creation: Date;
}

export interface FeedbackLink {
  link: string;
}

export interface DB {
  leaderboard: Leaderboard;
  feedbacklink: FeedbackLink;
}  
