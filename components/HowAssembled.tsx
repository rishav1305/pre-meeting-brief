/**
 * Legacy shim — kept so any external/test imports still resolve.
 *
 * The audit panel and the "how assembled" prose were consolidated into a
 * single `AuditPanel` component in Phase 3 polish A. Prefer importing
 * `AuditPanel` directly.
 */
export { AuditPanel as HowAssembled } from "./AuditPanel";
