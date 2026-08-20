import axios from "axios";

export type ApiDocument = {
  id: string;
  filename: string;
  document_type: string;
  status: string;
  thread_id?: string;
  current_node?: string;
  file_size_bytes: number;
  created_at: string;
  updated_at: string;
  vendor_name?: string | null;
  error_message?: string | null;
};
export type ApiCitation = { quote?: string; page_number?: number | null; section_header?: string | null; character_index?: number | null; line_number?: number | null };
export type ApiExtractedFact = { field_name: string; description: string; category: string; citation?: ApiCitation };
export type ApiUpperFact = { document_type?: string | null; client_name?: string | null; vendor_name?: string | null; summary?: string | null; facts: ApiExtractedFact[] };
export type ApiFact = { document_id: string; vendor_name?: string | null; client_name?: string | null; summary?: string | null; facts: ApiUpperFact };
export type ApiDocumentChunk = { chunk_index: number; content: string; metadata: { page_number?: number | null; page_start?: number | null; page_end?: number | null } };
export type ApiRelatedDocument = { id: string; filename: string; document_type: string; status: string; thread_id?: string };
export type ApiConflictSource = { citation?: ApiCitation; description?: string; doc_name?: string; document_id?: string; value?: string | number | boolean | null };
export type ApiConflict = {
  id: string;
  thread_id: string;
  field_name: string;
  status: string;
  description?: string;
  resolution?: string;
  conflicting_sources: ApiConflictSource[];
  created_at?: string;
};
export type ApiFinding = { id: string; thread_id: string; document_id: string; rule_id: string; description: string; citation: Record<string, unknown>; status: string };
export type ApiRule = { id: string; name: string; description: string; is_active: boolean };
export type CreateRule = { name: string; description: string };
export type ApiDeliverable = { id: string; title: string; content: string; version: number; related_document_ids: string[] };
export type ApiLibrarySummary = {
  document_count: number;
  in_pipeline: number;
  processed_this_month: number;
  transaction_count: number;
  needs_attention: number;
  pending_conflicts: number;
  pending_findings: number;
  active_transaction: { thread_id: string; document_count: number } | null;
  latest_activity: { thread_id: string; filename: string; event_type: string; message: string | null; created_at: string } | null;
};

const client = axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000", headers: { Accept: "application/json" } });

export const api = {
  listDocuments: () => client.get<ApiDocument[]>("/documents").then((r) => r.data),
  getLibrarySummary: () => client.get<ApiLibrarySummary>("/documents/summary").then((r) => r.data),
  getDocument: (id: string) => client.get<ApiDocument & { facts?: ApiFact; conflicts: ApiConflict[]; findings: ApiFinding[]; deliverable?: ApiDeliverable }>(`/documents/${id}`).then((r) => r.data),
  upload: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return client.post("/documents/upload", form).then((r) => r.data);
  },
  listConflicts: () => client.get<ApiConflict[]>("/conflicts").then((r) => r.data),
  listFindings: (threadId?: string) => client.get<ApiFinding[]>("/rules/findings", { params: threadId ? { thread_id: threadId } : undefined }).then((r) => r.data),
  listRules: () => client.get<ApiRule[]>("/rules").then((r) => r.data),
  createRules: (rules: CreateRule[]) => client.post<ApiRule[]>("/rules", { rules }).then((r) => r.data),
  deleteRule: (id: string) => client.delete<void>(`/rules/${id}`).then(() => undefined),
  listDeliverables: () => client.get<ApiDeliverable[]>("/deliverables").then((r) => r.data),
  resolveConflict: (thread_id: string, conflict_id: string, decision: "accept" | "reject") => client.post("/conflicts/resolve", { thread_id, decision: { conflict_id, decision } }),
  resolveFinding: (thread_id: string, rule_violation_id: string, decision: "accept" | "reject") => client.post("/rules/resolve", { thread_id, decision: { rule_violation_id, decision } }),
};
