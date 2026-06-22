import { createHash } from 'crypto';

/**
 * C5-REAL Compliant cryptographic signing
 */
export function generateClosureHash(payload: any, secretKey: string): string {
    const serialized = JSON.stringify(payload, Object.keys(payload).sort());
    const data = `${serialized}:${secretKey}`;
    return createHash('sha256').update(data).digest('hex');
}
