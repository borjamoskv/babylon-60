// NEXUS — UI Components (Vanilla JS)

export function createTrustRing(posteriorMean, tier, size = 56) {
  const r = (size - 4) / 2;
  const circumference = 2 * Math.PI * r;
  const offset = circumference * (1 - posteriorMean);
  const colors = {
    unverified: '#555570', bronze: '#CD7F32',
    silver: '#C0C0C0', gold: '#FFD700', sovereign: '#2B3BE5'
  };
  const color = colors[tier] || colors.unverified;

  return `<svg class="trust-ring" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
    <circle cx="${size/2}" cy="${size/2}" r="${r}" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="3"/>
    <circle cx="${size/2}" cy="${size/2}" r="${r}" fill="none" stroke="${color}" stroke-width="3"
      stroke-dasharray="${circumference}" stroke-dashoffset="${offset}"
      stroke-linecap="round" transform="rotate(-90 ${size/2} ${size/2})"
      style="transition: stroke-dashoffset 1.2s cubic-bezier(0.4,0,0.2,1)"/>
  </svg>`;
}

export function createAgentCard(agent) {
  const initial = agent.name.charAt(0);
  const trust = agent.trust || {};
  const tier = trust.tier || 'unverified';
  const mean = trust.posterior_mean || 0;
  const caps = (agent.capabilities || []).slice(0, 3);
  const status = agent.status || 'offline';

  return `<div class="agent-card" data-agent-id="${agent.id}" onclick="window.app.showAgent('${agent.id}')">
    <div class="agent-card-header">
      <div class="agent-avatar">
        ${createTrustRing(mean, tier)}
        <div class="agent-avatar-inner">${initial}</div>
      </div>
      <div>
        <div class="agent-name">${agent.name}</div>
        <div class="agent-owner">${agent.owner || 'Independent'}</div>
      </div>
      <div style="margin-left:auto; display:flex; align-items:center; gap:8px;">
        <div class="status-dot ${status}"></div>
        <span class="trust-badge ${tier}">${tier.toUpperCase()}</span>
      </div>
    </div>
    <div class="agent-desc">${agent.description || ''}</div>
    <div class="agent-footer">
      <div class="cap-badges">
        ${caps.map(c => `<span class="cap-badge">${c}</span>`).join('')}
      </div>
      <span style="font-family:var(--mono);font-size:11px;color:var(--text-muted);">μ=${mean.toFixed(3)}</span>
    </div>
  </div>`;
}

export function createActivityItem(event, index) {
  const iconMap = {
    registration: { cls: 'registration', icon: '⬡' },
    trust_verify: { cls: 'verify', icon: '✓' },
    trust_task_complete: { cls: 'task', icon: '◆' },
    trust_vouch: { cls: 'vouch', icon: '★' },
    task_created: { cls: 'task', icon: '📋' },
  };
  const ic = iconMap[event.event_type] || { cls: '', icon: '•' };
  const time = event.timestamp ? new Date(event.timestamp).toLocaleTimeString() : '';

  return `<div class="activity-item" style="animation-delay:${index * 0.05}s">
    <div class="activity-icon ${ic.cls}">${ic.icon}</div>
    <div class="activity-text">${event.description || event.event_type}</div>
    <div class="activity-time">${time}</div>
  </div>`;
}

export function createStatsBar(stats) {
  return `<div class="stats-bar">
    <div class="stat-card">
      <div class="stat-label">Total Agents</div>
      <div class="stat-value electric">${stats.total_agents || 0}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Verified</div>
      <div class="stat-value success">${stats.verified_agents || 0}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Online Now</div>
      <div class="stat-value" style="color:var(--text)">${stats.online_agents || 0}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Tasks Completed</div>
      <div class="stat-value gold">${stats.tasks_completed || 0}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Avg Trust</div>
      <div class="stat-value electric">${(stats.avg_trust_score || 0).toFixed(3)}</div>
    </div>
  </div>`;
}

export function createAgentDetail(agent) {
  const trust = agent.trust || {};
  const tier = trust.tier || 'unverified';
  const mean = trust.posterior_mean || 0;
  const tierColor = {
    unverified: 'var(--tier-unverified)', bronze: 'var(--tier-bronze)',
    silver: 'var(--tier-silver)', gold: 'var(--tier-gold)', sovereign: 'var(--tier-sovereign)'
  }[tier] || 'var(--text-muted)';

  return `<div class="agent-detail">
    <button class="back-btn" onclick="window.app.navigate('directory')">← Back to Directory</button>
    <div class="detail-header">
      <div class="detail-avatar">
        ${createTrustRing(mean, tier, 92)}
        <div class="agent-avatar-inner" style="font-size:32px">${agent.name.charAt(0)}</div>
      </div>
      <div style="flex:1">
        <div style="display:flex;align-items:center;gap:12px">
          <div class="detail-name">${agent.name}</div>
          <div class="status-dot ${agent.status}"></div>
          <span class="trust-badge ${tier}">${tier.toUpperCase()}</span>
        </div>
        <div class="detail-desc">${agent.description || ''}</div>
        <div style="margin-top:8px;display:flex;gap:6px;flex-wrap:wrap">
          ${(agent.capabilities||[]).map(c => `<span class="cap-badge">${c}</span>`).join('')}
        </div>
      </div>
    </div>

    <div class="detail-grid">
      <div class="detail-card">
        <div class="detail-card-title">Trust Score</div>
        <div style="display:flex;align-items:baseline;gap:8px">
          <span style="font-family:var(--mono);font-size:32px;font-weight:700;color:${tierColor}">${mean.toFixed(4)}</span>
          <span style="font-size:12px;color:var(--text-muted)">posterior mean</span>
        </div>
        <div class="trust-meter">
          <div class="trust-meter-fill" style="width:${mean*100}%;background:${tierColor}"></div>
        </div>
        <div style="display:flex;justify-content:space-between;margin-top:8px;font-family:var(--mono);font-size:11px;color:var(--text-muted)">
          <span>α=${(trust.alpha||0).toFixed(1)}</span>
          <span>β=${(trust.beta||0).toFixed(1)}</span>
          <span>signals=${trust.total_signals||0}</span>
        </div>
      </div>

      <div class="detail-card">
        <div class="detail-card-title">Performance</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:8px">
          <div>
            <div style="font-size:11px;color:var(--text-muted)">Tasks Completed</div>
            <div style="font-family:var(--mono);font-size:24px;font-weight:700;color:var(--success)">${agent.tasks_completed||0}</div>
          </div>
          <div>
            <div style="font-size:11px;color:var(--text-muted)">Tasks Failed</div>
            <div style="font-family:var(--mono);font-size:24px;font-weight:700;color:var(--danger)">${agent.tasks_failed||0}</div>
          </div>
        </div>
      </div>

      <div class="detail-card">
        <div class="detail-card-title">Identity</div>
        <div style="font-family:var(--mono);font-size:11px;color:var(--text-dim);word-break:break-all;margin-top:4px">
          ${agent.public_key || 'No key assigned'}
        </div>
        <div style="margin-top:8px;font-size:12px;color:var(--text-muted)">
          Owner: <strong style="color:var(--text)">${agent.owner||'—'}</strong>
        </div>
      </div>

      <div class="detail-card">
        <div class="detail-card-title">Metadata</div>
        <div style="font-size:12px;color:var(--text-dim);display:flex;flex-direction:column;gap:4px;margin-top:4px">
          <span>Registered: ${agent.registered_at ? new Date(agent.registered_at).toLocaleDateString() : '—'}</span>
          <span>Last Seen: ${agent.last_seen ? new Date(agent.last_seen).toLocaleString() : '—'}</span>
          <span>Agent ID: <code style="font-family:var(--mono);color:var(--electric)">${agent.id}</code></span>
        </div>
      </div>
    </div>
  </div>`;
}
