import { Keypair } from '@solana/web3.js';
import nacl from 'tweetnacl';
import bs58 from 'bs58';
import { config } from './config';

let keypair: Keypair | null = null;

function getKeypair(): Keypair {
  if (!keypair) {
    if (!config.privateKey) {
      throw new Error('PRIVATE_KEY not set in environment');
    }
    const secretKey = bs58.decode(config.privateKey);
    keypair = Keypair.fromSecretKey(secretKey);
  }
  return keypair;
}

export function signMessage(messageText: string): { signature: string; message: string } {
  const kp = getKeypair();
  const messageBytes = new TextEncoder().encode(messageText);
  const signatureBytes = nacl.sign.detached(messageBytes, kp.secretKey);
  return {
    signature: bs58.encode(signatureBytes),
    message: messageText,
  };
}
