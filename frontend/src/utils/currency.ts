export function formatMoney(amount: number, currency: string = 'USD'): string {
  return new Intl.NumberFormat(undefined, { style: 'currency', currency, minimumFractionDigits: 2, maximumFractionDigits: 4 }).format(amount);
}
export function currencySymbol(currency: string): string {
  return new Intl.NumberFormat(undefined, { style: 'currency', currency }).formatToParts(0).find(part => part.type === 'currency')?.value || currency;
}
