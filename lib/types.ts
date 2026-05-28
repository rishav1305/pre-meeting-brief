export type ThesisFitScore = 1 | 2 | 3 | 4 | 5;

export type AgendaItem = {
  event_id: string;
  meeting_date: string;
  company_domain: string;
  company_description: string | null;
  company_stage: string | null;
  company_last_round: string | null;
  thesis_fit_score: ThesisFitScore | null;
  brief_id: string | null;
};

export type AgendaResponse = {
  partner: string;
  items: AgendaItem[];
};
