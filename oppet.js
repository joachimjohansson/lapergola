// Öppettider från lapergola.se: alla dagar från kl. 16. Stängningstid anges inte på sajten,
// så sidan säger aldrig "stänger" eller "stängt nu" efter 16 – bara när vi öppnar.
const PERGOLA_OPENS = [16, 16, 16, 16, 16, 16, 16]; // index = getDay(), 0 = sön

// stangda: datum som "2026-12-24" från data-closed på öppettiderna
function pergolaStatus(now = new Date(), stangda = []) {
  const p2 = n => String(n).padStart(2, "0");
  const idag = `${now.getFullYear()}-${p2(now.getMonth() + 1)}-${p2(now.getDate())}`;
  if (stangda.includes(idag)) return { closedToday: true };
  const open = PERGOLA_OPENS[now.getDay()];
  const h = now.getHours() + now.getMinutes() / 60;
  return { open: h >= open, opens: p2(open), sunday: now.getDay() === 0 };
}

// Självtest (2026-11-08 är en söndag)
console.assert(pergolaStatus(new Date(2026, 10, 8, 15, 0)).open === false, "sön före 16");
console.assert(pergolaStatus(new Date(2026, 10, 8, 16, 0)).open === true, "sön 16");
console.assert(pergolaStatus(new Date(2026, 10, 8, 18, 0)).sunday === true, "söndag");
console.assert(pergolaStatus(new Date(2026, 10, 9, 18, 0)).sunday === false, "måndag");
console.assert(pergolaStatus(new Date(2026, 11, 24, 18, 0), ["2026-12-24"]).closedToday === true, "stängd dag");
