import axios from 'axios';
import { config } from './config';

export interface Market {
  publicKey: string;
  marketId: number;
  question: string;
  status: string;
  layer: string;
  outcome: string;
  yesPercent: number;
  noPercent: number;
  totalPoolSol: number;
  closingTime: string;
  isBettingOpen: boolean;
  category: string | null;
  creator: string;
  platformFeeBps: number;
}

export class BaoziAPI {
  private apiUrl: string;

  constructor() {
    this.apiUrl = config.apiUrl;
  }

  async getAllMarkets(): Promise<Market[]> {
    try {
      const response = await axios.get(`${this.apiUrl}/markets`);
      if (!response.data.success) throw new Error('API returned success: false');
      return response.data.data.binary || [];
    } catch (err) {
      console.error('Error fetching markets:', err);
      return [];
    }
  }

  async getLabMarkets(): Promise<Market[]> {
    const markets = await this.getAllMarkets();
    return markets.filter(m => m.layer === 'Lab');
  }

  async getActiveLabMarkets(): Promise<Market[]> {
    const labs = await this.getLabMarkets();
    return labs.filter(m => m.status === 'Active');
  }

  async postToAgentBook(content: string, marketPda?: string): Promise<boolean> {
    try {
      const body: any = {
        walletAddress: config.walletAddress,
        content,
      };
      if (marketPda) body.marketPda = marketPda;

      const response = await axios.post(`${this.apiUrl}/agentbook/posts`, body);
      if (response.data.success) {
        console.log(`✅ Posted to AgentBook`);
        return true;
      } else {
        console.error('AgentBook post failed:', response.data.error);
        return false;
      }
    } catch (err: any) {
      console.error('AgentBook error:', err.response?.data || err.message);
      return false;
    }
  }

  async commentOnMarket(marketPda: string, content: string, signature: string, message: string): Promise<boolean> {
    try {
      const response = await axios.post(
        `${this.apiUrl}/markets/${marketPda}/comments`,
        { content },
        {
          headers: {
            'x-wallet-address': config.walletAddress,
            'x-signature': signature,
            'x-message': message,
          },
        }
      );
      if (response.data.success) {
        console.log(`✅ Commented on market ${marketPda.substring(0, 8)}...`);
        return true;
      } else {
        console.error('Comment failed:', response.data.error);
        return false;
      }
    } catch (err: any) {
      console.error('Comment error:', err.response?.data || err.message);
      return false;
    }
  }
}
