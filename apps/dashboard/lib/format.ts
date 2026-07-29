const integer = new Intl.NumberFormat("es-ES", { maximumFractionDigits: 0 });
const currency = new Intl.NumberFormat("es-ES", {
  style: "currency",
  currency: "EUR",
  maximumFractionDigits: 0,
});

export function formatNumber(value: number, maximumFractionDigits = 1): string {
  return new Intl.NumberFormat("es-ES", { maximumFractionDigits }).format(value);
}

export function formatInteger(value: number): string {
  return integer.format(value);
}

export function formatCurrency(value: number): string {
  return currency.format(value);
}

export function formatDate(value: string, withTime = false): string {
  return new Intl.DateTimeFormat("es-ES", {
    day: "2-digit",
    month: "short",
    ...(withTime ? { hour: "2-digit", minute: "2-digit" } : {}),
    timeZone: "Europe/Madrid",
  }).format(new Date(value));
}

export function labelForCause(value: string): string {
  return (
    {
      soiling: "Suciedad progresiva",
      yaw_misalignment: "Desalineación de yaw",
      frozen_sensor: "Sensor congelado",
      underperformance: "Bajo rendimiento",
    }[value] ?? value.replaceAll("_", " ")
  );
}
