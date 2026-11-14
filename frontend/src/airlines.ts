const NAMES: Record<string, string> = {
  TK: 'Turkish Airlines', EK: 'Emirates', QR: 'Qatar Airways', EY: 'Etihad', SV: 'Saudia', MS: 'EgyptAir',
  RJ: 'Royal Jordanian', GF: 'Gulf Air', ME: 'Middle East Airlines', FZ: 'flydubai', XY: 'flynas', WY: 'Oman Air',
  LH: 'Lufthansa', LX: 'SWISS', OS: 'Austrian', SN: 'Brussels Airlines', EN: 'Air Dolomiti', EW: 'Eurowings',
  LO: 'LOT', A3: 'Aegean', AZ: 'ITA Airways', AF: 'Air France', KL: 'KLM', BA: 'British Airways', IB: 'Iberia',
  AY: 'Finnair', SK: 'SAS', TP: 'TAP', U2: 'easyJet', WK: 'Edelweiss', ET: 'Ethiopian', SQ: 'Singapore Airlines',
  AC: 'Air Canada', UA: 'United', AA: 'American', DL: 'Delta', VS: 'Virgin Atlantic', QF: 'Qantas', CX: 'Cathay Pacific',
  AI: 'Air India', KU: 'Kuwait Airways', PC: 'Pegasus', J9: 'Jazeera Airways', G9: 'Air Arabia',
}

export const airlineName = (code: string) => NAMES[code] ?? code
export const carrierOf = (flight: string) => flight.replace(/\s+/g, '').slice(0, 2).toUpperCase()

const HUES = [210, 262, 12, 152, 330, 38, 190, 100]
export function badgeColor(code: string): string {
  const h = HUES[(code.charCodeAt(0) * 7 + (code.charCodeAt(1) || 0)) % HUES.length]
  return `hsl(${h} 55% 42%)`
}
