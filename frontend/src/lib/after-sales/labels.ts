import type { ReturnReason, ReturnStatus, SupportSubject } from "./types";

export const RETURN_STATUS_LABELS: Record<ReturnStatus, string> = {
  requested: "Requested",
  approved: "Approved",
  rejected: "Rejected",
  received: "Received",
  refunded: "Refunded (demo)",
  cancelled: "Cancelled",
};

/** What each status means for the customer. */
export const RETURN_STATUS_HELP: Record<ReturnStatus, string> = {
  requested: "We have your request and will review it.",
  approved: "Approved. Please send the items back as agreed with our team.",
  rejected: "This return was not accepted.",
  received: "We received the items and are recording the refund.",
  refunded: "The refund was recorded manually (demo).",
  cancelled: "You cancelled this request.",
};

export const RETURN_REASON_LABELS: Record<ReturnReason, string> = {
  wrong_size: "Wrong size",
  damaged: "Item damaged",
  wrong_item: "Wrong item",
  not_as_expected: "Not as expected",
  changed_mind: "Changed mind",
  other: "Other",
};

export const SUBJECT_LABELS: Record<SupportSubject, string> = {
  sizing: "Sizing question",
  delivery: "Delivery question",
  order_issue: "Order issue",
  return_question: "Return question",
  other: "Other",
};

export const MESSAGE_MAX_LENGTH = 2000;
export const POLL_INTERVAL_MS = 4000;
