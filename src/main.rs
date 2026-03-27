pub mod cli;
pub mod context;
pub mod handlers;
pub mod hooks;
pub mod impact;
pub mod init;
pub mod memory;
pub mod paths;
pub mod recipes;
pub mod recover;
pub mod registry;
pub mod safety;
pub mod security;
pub mod server;
pub mod session;
pub mod sync;

use clap::Parser;
use cli::Cli;

#[tokio::main]
async fn main() {
    let cli = Cli::parse();
    cli.run().await;
}
