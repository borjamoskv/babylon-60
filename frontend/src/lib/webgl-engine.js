
export class CausalGraphEngine {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d', { alpha: false });
    this.width = window.innerWidth;
    this.height = window.innerHeight;
    
    // BABYLON-60 Mathematics
    this.base = 60;
    this.particles = [];
    this.mouse = { x: -1000, y: -1000, radius: 250 };
    
    // Theme Colors (Noir 2026)
    this.bg = '#050505';
    this.cobalt = 'rgba(43, 59, 229, 0.5)';
    this.kintsugi = 'rgba(245, 158, 11, 0.8)';
    
    this.init();
    this.bindEvents();
    this.animate();
  }

  init() {
    this.canvas.width = this.width;
    this.canvas.height = this.height;
    this.particles = [];
    
    // Create exactly 60 * 2 nodes for Base-60 resonance
    const count = 120;
    for(let i=0; i<count; i++) {
      this.particles.push({
        x: Math.random() * this.width,
        y: Math.random() * this.height,
        vx: (Math.random() - 0.5) * 0.5,
        vy: (Math.random() - 0.5) * 0.5,
        size: Math.random() * 2 + 1,
        baseX: 0,
        baseY: 0
      });
    }
  }

  bindEvents() {
    window.addEventListener('resize', () => {
      this.width = window.innerWidth;
      this.height = window.innerHeight;
      this.init();
    });
    
    window.addEventListener('mousemove', (e) => {
      this.mouse.x = e.clientX;
      this.mouse.y = e.clientY;
    });
  }

  animate() {
    requestAnimationFrame(() => this.animate());
    
    // Deep Noir Background
    this.ctx.fillStyle = this.bg;
    this.ctx.fillRect(0, 0, this.width, this.height);
    
    // Update and draw particles
    for(let i=0; i<this.particles.length; i++) {
      let p = this.particles[i];
      
      // Movement
      p.x += p.vx;
      p.y += p.vy;
      
      // Bounce
      if(p.x < 0 || p.x > this.width) p.vx *= -1;
      if(p.y < 0 || p.y > this.height) p.vy *= -1;
      
      // Mouse Gravity / Repulsion
      let dx = this.mouse.x - p.x;
      let dy = this.mouse.y - p.y;
      let dist = Math.sqrt(dx*dx + dy*dy);
      
      let isKintsugi = false;
      
      if(dist < this.mouse.radius) {
        let force = (this.mouse.radius - dist) / this.mouse.radius;
        // Gravity attraction
        p.x += dx * force * 0.02;
        p.y += dy * force * 0.02;
        if(force > 0.6) isKintsugi = true;
      }
      
      // Draw Node
      this.ctx.beginPath();
      this.ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
      this.ctx.fillStyle = isKintsugi ? this.kintsugi : this.cobalt;
      this.ctx.fill();
      
      // Draw Connections (Causal Links)
      for(let j=i+1; j<this.particles.length; j++) {
        let p2 = this.particles[j];
        let dx2 = p.x - p2.x;
        let dy2 = p.y - p2.y;
        let dist2 = Math.sqrt(dx2*dx2 + dy2*dy2);
        
        if(dist2 < 120) {
          this.ctx.beginPath();
          this.ctx.strokeStyle = `rgba(43, 59, 229, ${1 - dist2/120})`;
          this.ctx.lineWidth = 0.5;
          this.ctx.moveTo(p.x, p.y);
          this.ctx.lineTo(p2.x, p2.y);
          this.ctx.stroke();
        }
      }
    }
  }
}
