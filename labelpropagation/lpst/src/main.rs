//! # Label Propagation Demo
//!
//! This is a simple demonstration of the label propagation algorithm.
//! It creates a small example graph and runs the algorithm to show basic functionality.

use label_propagation::{Graph, LabelPropagation};
use std::collections::HashMap;
use std::fs;
use std::time::Instant;

fn main() {
    let start_time = Instant::now();
    
    // Example usage: Create a simple graph
    println!("Label Propagation Algorithm in Rust");
    println!("====================================\n");

    // Create a simple chain-like graph with 9 nodes
    // Edges form connections: 0-1-2-3-4-5-6-7-8
    let edges = vec![
        (0, 1), (0, 2),
        (1, 2), (1, 3),
        (2, 3), (2, 4),
        (3, 4), (3, 5),
        (4, 5), (4, 6),
        (5, 6), (5, 7),
        (6, 7), (6, 8),
        (7, 8),
    ];

    // Label some nodes (node_id -> label)
    // These are the "seed" nodes with known labels
    let mut labeled_nodes = HashMap::new();
    labeled_nodes.insert(0, 0);  // Node 0 has label 0 (left end)
    labeled_nodes.insert(8, 1);  // Node 8 has label 1 (right end)

    let graph = Graph::from_edge_list(edges, labeled_nodes);

    println!("Graph created with {} nodes", graph.nodes.len());
    println!("Initial labeled nodes: node 0 (label 0), node 8 (label 1)\n");

    // Run label propagation with max 100 iterations and 0.01 convergence threshold
    let lp = LabelPropagation::new(100, 0.01);
    let result = lp.propagate(&graph);

    println!("Results:");
    println!("--------");
    println!("Converged: {}", result.converged);
    println!("Iterations: {}", result.iterations);
    println!("\nNode Labels:");
    
    // Sort nodes by ID for consistent output
    let mut sorted_labels: Vec<_> = result.labels.iter().collect();
    sorted_labels.sort_by_key(|(id, _)| *id);
    
    for (node_id, label) in sorted_labels {
        println!("  Node {}: Label {}", node_id, label);
    }

    // Save results to JSON file for later analysis
    if let Ok(json) = serde_json::to_string_pretty(&result) {
        if let Err(e) = fs::write("label_propagation_result.json", json) {
            eprintln!("Error writing results: {}", e);
        } else {
            println!("\nResults saved to label_propagation_result.json");
        }
    }
    
    // Display total execution time
    let elapsed = start_time.elapsed();
    println!("\nTotal execution time: {:.3}s ({:.2}ms)", elapsed.as_secs_f64(), elapsed.as_micros() as f64 / 1000.0);
}
