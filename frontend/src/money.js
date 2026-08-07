/** Formatting for amounts and dates.
 *
 *  One place, because a balance shown as "9645.49" in the topbar and "$9,645.49"
 *  on the account page reads as two different numbers. */

export function currency(value, code = "USD") {
  const amount = Number(value ?? 0);
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: code,
    minimumFractionDigits: 2,
  }).format(amount);
}

/** Signed, for a ledger line: "+$1,240.00" / "−$54.05". */
export function signedCurrency(value, code = "USD") {
  const amount = Number(value ?? 0);
  const formatted = currency(Math.abs(amount), code);
  if (amount > 0) return `+${formatted}`;
  if (amount < 0) return `−${formatted}`;
  return formatted;
}

export function shortDate(value) {
  return new Date(value).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

export function fullDate(value) {
  return new Date(value).toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}
