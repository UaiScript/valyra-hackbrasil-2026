const currency = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
export const money = (cents: number) => currency.format(cents / 100);
// Datas do domínio são dias civis: meio-dia explícito evita recuo por conversão UTC/local.
export const shortDate = (iso: string) =>
  new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: 'short' }).format(
    new Date(`${iso}T12:00:00`),
  );
