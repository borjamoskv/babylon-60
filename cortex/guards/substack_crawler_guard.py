"""
[C5-REAL] Substack Crawler Inflation Guard
Enforces OUROBOROS-014 (INV_PPI_START_ZERO), OUROBOROS-094 (INV_OBSERVATION_LOOP).
Purges estocastic sensor drift from B2B PR inboxes mimicking as human engagement.
"""

from typing import Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)

# AP-01: No Green Theater here. Strict filtering arrays.
STOCHASTIC_NOISE_DOMAINS = {
    'gmail.com', 'hotmail.com', 'yahoo.es', 'yahoo.com', 'outlook.com', 
    'icloud.com', 'protonmail.com', 'me.com', 'mac.com', 'live.com',
    'msn.com', 'pm.me', 'proton.me', 'gmx.com', 'yandex.ru', 'mail.com'
}

# Signatures of Corporate Firewalls / Dead Letter Inboxes (Sensor Corruptors)
CRAWLER_BOT_PREFIXES = {
    'press', 'demos', 'info', 'editorial', 'news', 'submissions', 'contact',
    'hello', 'hi', 'admin', 'marketing', 'pr', 'support', 'team', 'hola', 'webmaster'
}

def op_extract_signal(email: str, opens: int, clicks: int) -> Tuple[bool, str]:
    """
    APEX-023: OP_EXTRACT_SIGNAL
    Filters out Crawler Bot Inflation and Epistemic Limerence from SaaS metrics.
    
    Returns:
        Tuple[bool, str]: (Is_Human_VIP_Signal, Classification_Reason)
    """
    if not email or '@' not in email:
        return False, "INVALID_FORMAT"
        
    local_part, domain = email.lower().split('@', 1)
    
    # 1. Purge B2C Stochastic Noise (Normal readers, not SOTA Nodes)
    if domain in STOCHASTIC_NOISE_DOMAINS:
        return False, "B2C_STOCHASTIC_NOISE"
        
    # 2. Detect Corporate Crawler Inflation (APEX-019 TAINT SCAN)
    if local_part in CRAWLER_BOT_PREFIXES:
        # High opens with zero/massive clicks on a generic inbox = Bot Firewall
        if opens > 100:
            logger.warning(f"[CRAWLER DETECTED] High open rate on PR dead-inbox: {email}")
            return False, "CRAWLER_INFLATION_BOT"
        return False, "CORPORATE_DEAD_INBOX"
        
    # 3. Ratio-Based Drift Detection (APEX-034 OP_OOM_SIM execution on assumption)
    # If clicks == opens and > 50, it's a Proofpoint/Barracuda link scanner.
    if opens > 50 and clicks > 0 and abs(opens - clicks) <= 2:
        return False, "FIREWALL_LINK_SCANNER"

    # If it survived, it is a nominal human operating from a SOTA institutional domain.
    return True, "SOTA_NOMINAL_HUMAN"

def enforce_substack_reality(subscriber_record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Applies BFT Quorum isolation against Substack's optimistic metrics.
    """
    email = subscriber_record.get('Email', '')
    opens = int(subscriber_record.get('Emails opened (6mo)', 0))
    clicks = int(subscriber_record.get('Links clicked', 0))
    
    is_vip, reason = op_extract_signal(email, opens, clicks)
    
    # Inject Exergy Flag (CORTEX-TAINT equivalent)
    subscriber_record['CORTEX_VIP_SIGNAL'] = is_vip
    subscriber_record['CORTEX_SIGNAL_REASON'] = reason
    
    if not is_vip and opens > 0:
        # Apoptosis on corrupted metrics
        subscriber_record['REALITY_ADJUSTED_OPENS'] = 0 
    else:
        subscriber_record['REALITY_ADJUSTED_OPENS'] = opens
        
    return subscriber_record
