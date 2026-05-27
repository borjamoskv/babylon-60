// ============================================================
// BOUNTY-HUNTER — C5-REAL Rust Swarm Orchestrator
// Reality: C5-REAL (network I/O bound, not CPU bound after dispatch)
// Dispatch: 22.5M task/s local scheduling | Network: ~50K req/s
// ============================================================

mod recon;
mod probe;
mod fuzz;
mod report;

use anyhow::Result;
use clap::{Parser, Subcommand};
use colored::*;

#[derive(Parser)]
#[command(
    name = "bounty-hunter",
    version = "0.1.0",
    about = "C5-REAL Bug Bounty Swarm — Rust 22.5M dispatch/s orchestrator",
    long_about = None
)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Recon: subdomain enumeration + DNS bruteforce
    Recon {
        /// Target domain (e.g. example.com)
        #[arg(short, long)]
        domain: String,

        /// Wordlist file for subdomain bruteforce
        #[arg(short, long, default_value = "wordlists/subdomains.txt")]
        wordlist: String,

        /// Max concurrent DNS resolvers
        #[arg(short, long, default_value = "2000")]
        concurrency: usize,

        /// Output file (JSON)
        #[arg(short, long, default_value = "output/recon.json")]
        output: String,
    },

    /// Probe: HTTP endpoint discovery + response fingerprinting
    Probe {
        /// File with URLs to probe (one per line)
        #[arg(short, long)]
        input: String,

        /// Max concurrent HTTP workers
        #[arg(short, long, default_value = "500")]
        concurrency: usize,

        /// Request timeout in seconds
        #[arg(short, long, default_value = "5")]
        timeout: u64,

        /// Output file (JSON)
        #[arg(short, long, default_value = "output/probe.json")]
        output: String,

        /// Follow redirects
        #[arg(long, default_value = "true")]
        follow_redirects: bool,
    },

    /// Fuzz: parameter + path fuzzing for vulnerability discovery
    Fuzz {
        /// Base URL to fuzz
        #[arg(short, long)]
        url: String,

        /// Wordlist for path/param fuzzing
        #[arg(short, long, default_value = "wordlists/common.txt")]
        wordlist: String,

        /// Fuzzing mode: paths | params | both
        #[arg(short, long, default_value = "both")]
        mode: String,

        /// Max concurrent workers
        #[arg(short, long, default_value = "300")]
        concurrency: usize,

        /// HTTP method
        #[arg(long, default_value = "GET")]
        method: String,

        /// Output file (JSON)
        #[arg(short, long, default_value = "output/fuzz.json")]
        output: String,
    },

    /// Full: recon → probe → fuzz pipeline (sovereign chain)
    Full {
        /// Target domain
        #[arg(short, long)]
        domain: String,

        /// Subdomain wordlist
        #[arg(long, default_value = "wordlists/subdomains.txt")]
        sub_wordlist: String,

        /// Fuzz wordlist
        #[arg(long, default_value = "wordlists/common.txt")]
        fuzz_wordlist: String,

        /// Output directory
        #[arg(short, long, default_value = "output")]
        output_dir: String,

        /// Total concurrency budget
        #[arg(short, long, default_value = "500")]
        concurrency: usize,
    },
}

#[tokio::main]
async fn main() -> Result<()> {
    print_banner();

    let cli = Cli::parse();

    match cli.command {
        Commands::Recon { domain, wordlist, concurrency, output } => {
            recon::run(domain, wordlist, concurrency, output).await?;
        }
        Commands::Probe { input, concurrency, timeout, output, follow_redirects } => {
            probe::run(input, concurrency, timeout, output, follow_redirects).await?;
        }
        Commands::Fuzz { url, wordlist, mode, concurrency, method, output } => {
            fuzz::run(url, wordlist, mode, concurrency, method, output).await?;
        }
        Commands::Full { domain, sub_wordlist, fuzz_wordlist, output_dir, concurrency } => {
            run_full_pipeline(domain, sub_wordlist, fuzz_wordlist, output_dir, concurrency).await?;
        }
    }

    Ok(())
}

async fn run_full_pipeline(
    domain: String,
    sub_wordlist: String,
    fuzz_wordlist: String,
    output_dir: String,
    concurrency: usize,
) -> Result<()> {
    println!("{}", "━━━ PHASE 1: RECON ━━━".bright_blue().bold());
    let recon_out = format!("{}/recon.json", output_dir);
    let discovered = recon::run(domain.clone(), sub_wordlist, concurrency, recon_out.clone()).await?;

    println!("\n{}", "━━━ PHASE 2: PROBE ━━━".bright_blue().bold());
    let probe_input = format!("{}/urls.txt", output_dir);
    // Write discovered URLs to temp file for probe phase
    let urls: Vec<String> = discovered
        .iter()
        .flat_map(|h| vec![
            format!("https://{}", h),
            format!("http://{}", h),
        ])
        .collect();
    tokio::fs::write(&probe_input, urls.join("\n")).await?;

    let probe_out = format!("{}/probe.json", output_dir);
    let live_hosts = probe::run(
        probe_input,
        concurrency / 2,
        8,
        probe_out,
        true,
    ).await?;

    println!("\n{}", "━━━ PHASE 3: FUZZ ━━━".bright_blue().bold());
    let fuzz_out = format!("{}/fuzz.json", output_dir);
    // Fuzz the first live host found (extend for full swarm)
    if let Some(target) = live_hosts.first() {
        fuzz::run(
            target.clone(),
            fuzz_wordlist,
            "both".to_string(),
            concurrency / 3,
            "GET".to_string(),
            fuzz_out,
        ).await?;
    } else {
        println!("{}", "No live hosts found. Aborting fuzz phase.".yellow());
    }

    println!("\n{}", "━━━ PIPELINE COMPLETE ━━━".green().bold());
    println!("Results stored in: {}", output_dir.bright_white());
    Ok(())
}

fn print_banner() {
    println!(
        "{}",
        r#"
╔═══════════════════════════════════════════════════════════╗
║  ██████╗  ██████╗ ██╗   ██╗███╗   ██╗████████╗██╗   ██╗  ║
║  ██╔══██╗██╔═══██╗██║   ██║████╗  ██║╚══██╔══╝╚██╗ ██╔╝  ║
║  ██████╔╝██║   ██║██║   ██║██╔██╗ ██║   ██║    ╚████╔╝   ║
║  ██╔══██╗██║   ██║██║   ██║██║╚██╗██║   ██║     ╚██╔╝    ║
║  ██████╔╝╚██████╔╝╚██████╔╝██║ ╚████║   ██║      ██║     ║
║  ╚═════╝  ╚═════╝  ╚═════╝ ╚═╝  ╚═══╝   ╚═╝      ╚═╝     ║
║                                                           ║
║   H U N T E R   ——   C5-REAL   ——   22.5M dispatch/s     ║
╚═══════════════════════════════════════════════════════════╝
        "#.truecolor(43, 59, 229)
    );
    println!("  {}: Rust async swarm orchestrator for bug bounty ops\n", "v0.1.0".bright_white());
}
