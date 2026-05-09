import type { ProblemResponse, SubmissionDetailResponse, LanguageConfigResponse } from "@/lib/api-client";

export type ProblemWithDescription = ProblemResponse;

export interface SubmissionCaseDetail {
  test_case_id: string;
  input?: string | null;
  expected?: string | null;
  actual?: string | null;
  verdict?: string | null;
  stdout?: string | null;
}

export interface SubmissionDetailResponseWithCases extends SubmissionDetailResponse {
  details?: SubmissionCaseDetail[];
}

export type LanguageConfigMap = Record<string, LanguageConfigResponse>;
