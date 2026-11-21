/** Shapes returned by the FastAPI backend (see backend/app/api). */

export interface FixedCost { name: string; amount: number }

export interface Profile {
  monthly_income: number | null;
  fixed_costs: FixedCost[];
  emergency_fund: number;
  emergency_target_months: number;
  emergency_monthly: number;
  budgets: Record<string, number>;
}

export interface Goal {
  id: number | string;
  name: string;
  kind: "goal" | "emergency";
  target: number;
  saved: number;
  target_date: string | null;
  planned: number;
  remaining: number;
  contribution: number;
  pct: number;
  required_monthly: number | null;
  months_to_go: number | null;
  projected_date: string | null;
  on_track: boolean;
  gap: number;
}

export interface Snapshot {
  as_of: string;
  income: number;
  spend: number;
  free_cash: number;
  invested: number;
  by_cat: Record<string, number>;
  emergency_months: number | null;
  goals: { items: Goal[]; planned_total: number; scale: number };
}

export interface MonthSummary {
  month: string;
  income: number;
  spend: number;
  invested: number;
  by_cat: Record<string, number>;
}

export interface Summary {
  empty: boolean;
  as_of: string;
  months: MonthSummary[];
  snapshot: Snapshot;
  profile: Profile;
  tx_count: number;
  uncategorized: number;
}

export interface Health {
  ok: boolean;
  ai_enabled: boolean;
  ai: { available: boolean | null; last_error: string | null; model: string | null };
  disclaimer: string;
}

export type Severity = "alert" | "warn" | "info";

export interface Nudge {
  id: string;
  kind: "budget" | "spike" | "goal" | "emergency" | "subscription";
  severity: Severity;
  title: string;
  body: string;
  category?: string;
}

export interface NudgeExplanation { explanation?: string; ai?: boolean; loading?: boolean }

export interface Tx {
  id: number;
  date: string;
  description: string;
  amount: number;
  merchant: string;
  category: string;
  cat_source: string;
  source: "csv" | "pdf" | "sms";
}

export interface Rule { id: number; pattern: string; category: string; hits: number }

export interface ImportReport {
  format: string;
  parsed: number;
  added: number;
  duplicates_skipped: number;
  categorized_by: Record<string, number>;
  notes: string[];
}

export interface CorrectionResult { merchant: string; rule_created: boolean; also_updated: number }

export interface SubAlert { type: string; severity: Severity; message: string }

export interface Subscription {
  merchant: string;
  kind: "subscription" | "bill" | "saving";
  cadence: string;
  amount: number;
  fixed_amount: boolean;
  count: number;
  first_date: string;
  next_date: string;
  last_used: string | null;
  autopay: boolean;
  alerts: SubAlert[];
}

export interface Mandate {
  merchant: string;
  name: string;
  amount: number;
  date: string;
  current_amount: number | null;
  changed: boolean;
}

export interface SubscriptionsResponse { items: Subscription[]; mandates: Mandate[]; monthly_total: number }

export interface GoalsResponse { items: Goal[]; free_cash: number; planned_total: number; scale: number }

export interface GoalChange {
  id: number | string;
  name: string;
  target_date: string | null;
  before_date: string | null;
  after_date: string | null;
  shift_months: number | null;
  before_on_track: boolean;
  after_on_track: boolean;
}

export interface WhatIfResult {
  before: Snapshot;
  after: Snapshot;
  delta_free_cash: number;
  delta_yearly: number;
  summary: string;
  goal_changes: GoalChange[];
}

export interface LifeEventInput {
  type: "salary_change" | "job_loss" | "rent_increase" | "new_emi";
  start: number;
  percent?: number;
  months?: number;
  amount?: number;
  cut_pct?: number;
}

export interface LifeSeries {
  ef: number[];
  ef_target: number;
  ef_low: number;
  ef_low_month: number;
  ef_depleted_month: number | null;
  as_of: string;
}

export interface LifeGoal {
  id: number | string;
  name: string;
  target_date: string | null;
  before_date: string | null;
  after_date: string | null;
  shift_months: number | null;
  before_on_track: boolean;
  after_on_track: boolean;
  not_in_horizon: boolean;
}

export interface LifeSim {
  labels: string[];
  before: LifeSeries;
  after: LifeSeries;
  goals: LifeGoal[];
  marks: { month: number; label: string }[];
  ef_runway_low_months: number;
  summary: string;
}

export interface Narration { text: string; ai: boolean }

export interface TimelineEvent { date: string; kind: string; title: string; detail?: string; why?: string; source: "logged" | "detected" }

export interface ReviewFacts {
  month: string;
  partial_month: boolean;
  income: number;
  spend: number;
  left_over: number;
  savings_rate_pct: number | null;
  top_categories: { category: string; amount: number; share_pct: number }[];
  budgets: { category: string; budget: number; spent: number; status: "over" | "within" }[];
}

export interface Review { facts: ReviewFacts; narrative: string; ai: boolean; months: string[] }

export interface Step { tool: string; args: Record<string, unknown>; result?: string }

export interface Proposal { id: number; kind: string; description: string; reason: string | null }

export interface ChatReply {
  reply: string;
  ai: boolean;
  guardrail: boolean;
  cached: boolean;
  tools: Step[];
  proposals: Proposal[];
}

export interface ChatHistory { messages: { role: "user" | "model"; text: string }[]; proposals: Proposal[] }
