import { generateClosureHash } from './crypto';

export interface CortexClientOptions {
    apiKey: string;
    endpoint?: string;
    tenantId?: string;
}

export interface CortexEvent {
    type: string;
    actor: string;
    payload?: any;
    timestamp?: number;
}

export class CortexClient {
    private apiKey: string;
    private endpoint: string;
    private tenantId: string;

    constructor(options: CortexClientOptions) {
        if (!options.apiKey) {
            throw new Error("CORTEX-Persist: apiKey is required.");
        }
        this.apiKey = options.apiKey;
        this.endpoint = options.endpoint || "https://edge.cortexpersist.com/v1/events";
        this.tenantId = options.tenantId || "default";
    }

    /**
     * Injects an event into the CORTEX Epistemic Graph.
     * C5-REAL Compliant: Hashes payload locally before transmission.
     */
    async logEvent(event: CortexEvent): Promise<any> {
        const timestamp = event.timestamp || Math.floor(Date.now() / 1000 * 60); // Babylon-60 Base

        const payload = {
            ...event,
            timestamp,
            tenantId: this.tenantId
        };

        const hash = generateClosureHash(payload, this.apiKey);

        const response = await fetch(this.endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.apiKey}`,
                'X-Cortex-Taint': hash
            },
            body: JSON.stringify({
                payload,
                signature: hash
            })
        });

        if (!response.ok) {
            throw new Error(`CORTEX-Persist: Failed to log event. Status: ${response.status}`);
        }

        return await response.json();
    }
}
