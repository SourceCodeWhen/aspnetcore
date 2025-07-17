#!/usr/bin/env python3
"""
Git Commit Graph Generator
Generates a graph of all commits to all branches from a given point in time to the current day.
"""

import argparse
import sys
from datetime import datetime, timezone
from collections import defaultdict
import json

try:
    import git
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import networkx as nx
    import numpy as np
    from matplotlib.patches import Rectangle
except ImportError as e:
    print(f"Error: Required package not installed: {e}")
    print("Install with: pip install GitPython matplotlib networkx numpy")
    sys.exit(1)


def get_all_commits_from_date(repo_path, since_date):
    """
    Get all commits from all branches since the specified date.
    
    Args:
        repo_path (str): Path to the git repository
        since_date (datetime): Date to start collecting commits from
        
    Returns:
        dict: Dictionary with branch names as keys and commit lists as values
    """
    try:
        repo = git.Repo(repo_path)
    except git.exc.InvalidGitRepositoryError:
        print(f"Error: '{repo_path}' is not a valid Git repository")
        sys.exit(1)
    
    all_commits = defaultdict(list)
    
    # Get all branches (local and remote)
    branches = []
    
    # Add local branches
    for branch in repo.branches:
        branches.append(branch.name)
    
    # Add remote branches
    for remote in repo.remotes:
        for ref in remote.refs:
            branch_name = f"{remote.name}/{ref.name.split('/')[-1]}"
            if branch_name not in branches:
                branches.append(branch_name)
    
    print(f"Found {len(branches)} branches")
    
    # Collect commits from each branch
    for branch_name in branches:
        try:
            # Get commits from the branch since the specified date
            commits = list(repo.iter_commits(
                branch_name, 
                since=since_date.strftime('%Y-%m-%d')
            ))
            
            if commits:
                all_commits[branch_name] = commits
                print(f"Branch '{branch_name}': {len(commits)} commits")
        
        except git.exc.GitCommandError as e:
            print(f"Warning: Could not access branch '{branch_name}': {e}")
            continue
    
    return all_commits


def create_commit_timeline_graph(all_commits, output_file="commit_timeline.png"):
    """
    Create a timeline graph showing commits across all branches.
    
    Args:
        all_commits (dict): Dictionary with branch names and their commits
        output_file (str): Output filename for the graph
    """
    if not all_commits:
        print("No commits found in the specified time range")
        return
    
    # Prepare data for plotting
    branch_names = list(all_commits.keys())
    colors = plt.cm.Set3(np.linspace(0, 1, len(branch_names)))
    
    fig, ax = plt.subplots(figsize=(15, max(8, len(branch_names) * 0.5)))
    
    # Plot commits for each branch
    for i, (branch, commits) in enumerate(all_commits.items()):
        dates = [datetime.fromtimestamp(commit.authored_date, tz=timezone.utc) 
                for commit in commits]
        y_pos = [i] * len(dates)
        
        # Plot commits as scatter points
        ax.scatter(dates, y_pos, c=[colors[i]], alpha=0.7, s=20, label=branch)
        
        # Add commit count annotation
        if dates:
            ax.annotate(f'{len(commits)} commits', 
                       xy=(max(dates), i), 
                       xytext=(5, 0), 
                       textcoords='offset points',
                       va='center', fontsize=8)
    
    # Customize the plot
    ax.set_yticks(range(len(branch_names)))
    ax.set_yticklabels([name[:30] + '...' if len(name) > 30 else name 
                       for name in branch_names])
    ax.set_xlabel('Date')
    ax.set_ylabel('Branches')
    ax.set_title('Git Commit Timeline Across All Branches')
    
    # Format x-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
    plt.xticks(rotation=45)
    
    # Add grid
    ax.grid(True, alpha=0.3)
    
    # Adjust layout and save
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Timeline graph saved to {output_file}")


def create_commit_network_graph(all_commits, output_file="commit_network.png"):
    """
    Create a network graph showing relationships between commits and branches.
    
    Args:
        all_commits (dict): Dictionary with branch names and their commits
        output_file (str): Output filename for the graph
    """
    if not all_commits:
        print("No commits found in the specified time range")
        return
    
    # Create a directed graph
    G = nx.DiGraph()
    
    # Add nodes and edges
    for branch, commits in all_commits.items():
        # Add branch node
        G.add_node(branch, node_type='branch', commit_count=len(commits))
        
        # Add commit nodes and connect to branch
        for commit in commits[:10]:  # Limit to first 10 commits for readability
            commit_id = commit.hexsha[:8]
            G.add_node(commit_id, 
                      node_type='commit',
                      author=commit.author.name,
                      date=commit.authored_date,
                      message=commit.message[:50])
            G.add_edge(branch, commit_id)
    
    # Create the plot
    fig, ax = plt.subplots(figsize=(15, 10))
    
    # Position nodes
    pos = nx.spring_layout(G, k=1, iterations=50)
    
    # Draw branch nodes
    branch_nodes = [n for n in G.nodes() if G.nodes[n].get('node_type') == 'branch']
    nx.draw_networkx_nodes(G, pos, nodelist=branch_nodes, 
                          node_color='lightblue', node_size=1000, ax=ax)
    
    # Draw commit nodes
    commit_nodes = [n for n in G.nodes() if G.nodes[n].get('node_type') == 'commit']
    nx.draw_networkx_nodes(G, pos, nodelist=commit_nodes, 
                          node_color='lightcoral', node_size=300, ax=ax)
    
    # Draw edges
    nx.draw_networkx_edges(G, pos, edge_color='gray', alpha=0.5, ax=ax)
    
    # Draw labels
    nx.draw_networkx_labels(G, pos, font_size=8, ax=ax)
    
    ax.set_title('Git Commit Network Graph')
    ax.axis('off')
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Network graph saved to {output_file}")


def create_summary_stats(all_commits, output_file="commit_summary.json"):
    """
    Create a summary statistics file.
    
    Args:
        all_commits (dict): Dictionary with branch names and their commits
        output_file (str): Output filename for the summary
    """
    summary = {
        'total_branches': len(all_commits),
        'total_commits': sum(len(commits) for commits in all_commits.values()),
        'branch_stats': {}
    }
    
    for branch, commits in all_commits.items():
        if commits:
            authors = list(set(commit.author.name for commit in commits))
            summary['branch_stats'][branch] = {
                'commit_count': len(commits),
                'unique_authors': len(authors),
                'authors': authors,
                'latest_commit': commits[0].authored_date if commits else None,
                'oldest_commit': commits[-1].authored_date if commits else None
            }
    
    with open(output_file, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    
    print(f"Summary statistics saved to {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Generate a graph of all Git commits from all branches since a given date'
    )
    parser.add_argument(
        '--since', 
        type=str, 
        required=True,
        help='Start date in YYYY-MM-DD format'
    )
    parser.add_argument(
        '--repo-path', 
        type=str, 
        default='.',
        help='Path to the Git repository (default: current directory)'
    )
    parser.add_argument(
        '--output-dir', 
        type=str, 
        default='.',
        help='Output directory for generated files (default: current directory)'
    )
    
    args = parser.parse_args()
    
    # Parse the since date
    try:
        since_date = datetime.strptime(args.since, '%Y-%m-%d')
        since_date = since_date.replace(tzinfo=timezone.utc)
    except ValueError:
        print("Error: Invalid date format. Use YYYY-MM-DD")
        sys.exit(1)
    
    print(f"Collecting commits since {args.since} from repository: {args.repo_path}")
    
    # Get all commits
    all_commits = get_all_commits_from_date(args.repo_path, since_date)
    
    if not all_commits:
        print("No commits found in the specified time range")
        return
    
    # Generate output files
    import os
    timeline_file = os.path.join(args.output_dir, "commit_timeline.png")
    network_file = os.path.join(args.output_dir, "commit_network.png")
    summary_file = os.path.join(args.output_dir, "commit_summary.json")
    
    create_commit_timeline_graph(all_commits, timeline_file)
    create_commit_network_graph(all_commits, network_file)
    create_summary_stats(all_commits, summary_file)
    
    print(f"\nGenerated files:")
    print(f"- Timeline graph: {timeline_file}")
    print(f"- Network graph: {network_file}")
    print(f"- Summary stats: {summary_file}")


if __name__ == "__main__":
    main()
