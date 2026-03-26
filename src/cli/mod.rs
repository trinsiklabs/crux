//! CLI interface via clap.

use clap::Parser;

#[derive(Parser)]
#[command(name = "crux", about = "Self-improving AI operating system")]
pub struct Cli {
    #[command(subcommand)]
    command: Option<Commands>,
}

#[derive(clap::Subcommand)]
enum Commands {
    /// Show runtime status and health checks
    Status,
    /// Switch to a different AI tool
    Switch { tool: String },
    /// Run health checks
    Health,
    /// Search knowledge entries
    Knowledge { query: String },
    /// Find files relevant to a task
    Impact { prompt: String, #[arg(default_value = "10")] top_n: usize },
    /// Show daily digest
    Digest,
    /// MCP server management
    Mcp {
        #[command(subcommand)]
        cmd: McpCommands,
    },
    /// Interactive setup
    Setup,
    /// Show version
    Version,
}

#[derive(clap::Subcommand)]
enum McpCommands {
    /// Start MCP server on stdio
    Start,
    /// Show server status and tools
    Status,
    /// List all tool names
    Tools,
}

impl Cli {
    pub async fn run(self) {
        match self.command {
            Some(Commands::Version) | None => {
                println!("crux {}", env!("CARGO_PKG_VERSION"));
            }
            Some(Commands::Status) => println!("Status: TODO"),
            Some(Commands::Health) => println!("Health: TODO"),
            Some(Commands::Switch { tool }) => println!("Switch to {tool}: TODO"),
            Some(Commands::Knowledge { query }) => println!("Knowledge '{query}': TODO"),
            Some(Commands::Impact { prompt, top_n }) => println!("Impact '{prompt}' top {top_n}: TODO"),
            Some(Commands::Digest) => println!("Digest: TODO"),
            Some(Commands::Mcp { cmd }) => match cmd {
                McpCommands::Start => println!("MCP start: TODO"),
                McpCommands::Status => println!("MCP status: TODO"),
                McpCommands::Tools => println!("MCP tools: TODO"),
            },
            Some(Commands::Setup) => println!("Setup: TODO"),
        }
    }
}
