# Usage Examples

This document provides practical examples of using the Talos MCP Server with Claude.

## Getting Started

Once you've configured the MCP server in Claude Desktop, you can interact with your Talos cluster using natural language. Claude will automatically use the appropriate tools based on your requests.

## Common Tasks

### 1. Cluster Health & Status

**Check cluster health:**
```
Claude, check the health of my Talos cluster
```

**Get cluster version:**
```
What version of Talos is running on my cluster?
```

**View running services:**
```
Show me all services running on node 192.168.1.10
```

**Get a dashboard snapshot:**
```
Give me a snapshot of resource usage across my cluster
```

### 2. Node Management

**List disks on a node:**
```
List all disks on nodes 192.168.1.10 and 192.168.1.11
```

**View node resources:**
```
Show me all Talos resources on my control plane nodes
```

**Get node configuration:**
```
What's the machine configuration for node 192.168.1.10?
```

### 3. Debugging & Logs

**View service logs:**
```
Show me the last 100 lines of kubelet logs from node 192.168.1.10
```

**Check etcd logs:**
```
Get etcd logs from my control plane nodes
```

**View container logs:**
```
Show me logs from the coredns container on node 192.168.1.11
```

**Browse filesystem:**
```
List files in /var/log on node 192.168.1.10
```

**Read a file:**
```
Read the contents of /etc/resolv.conf on node 192.168.1.10
```

### 4. Cluster Configuration

**View current configuration:**
```
What's my current Talos configuration and context?
```

**Get kubeconfig:**
```
Generate and show me the kubeconfig for my cluster
```

**Check etcd members:**
```
List all etcd cluster members
```

### 5. Advanced Queries

**Resource inspection:**
```
Show me all resource definitions available in Talos
```

**Get specific resources:**
```
Get the member list in JSON format
```

**Check network configuration:**
```
What network interfaces are configured on node 192.168.1.10?
```

**View machine status:**
```
Show me the machine status for all my control plane nodes
```

## Multi-Step Workflows

### Troubleshooting a Node

```
1. "Check the health of node 192.168.1.10"
2. "Show me the kubelet logs from that node"
3. "List all running services on that node"
4. "What's the disk usage on that node?"
```

### Setting Up a New Node

```
1. "List available disks on node 192.168.1.15 using insecure mode"
2. "Show me the current configuration"
3. "What services should be running on a worker node?"
```

### Monitoring Cluster

```
1. "Check the health of my entire cluster"
2. "Show me etcd members"
3. "Get a dashboard snapshot"
4. "What's the version of Talos running on all nodes?"
```

## Tips for Best Results

### Be Specific with Node IPs

Instead of:
```
Show me the logs
```

Use:
```
Show me kubelet logs from node 192.168.1.10
```

### Specify Output Format When Needed

```
Get the member list in JSON format
```

```
Show me services in YAML format
```

### Use Resource Types Correctly

Talos has many resource types. To discover them:
```
Show me all available resource definitions
```

Then query specific resources:
```
Get the NodeAddress resources
```

```
Show me the TimeStatus resources
```

### Combine Multiple Requests

Claude can perform multiple operations:
```
Check the health of my cluster, then show me the etcd members, 
and finally get the kubelet logs from any unhealthy nodes
```

## Common Use Cases

### 1. Daily Cluster Check

```
Claude, give me a comprehensive status of my Talos cluster including:
- Overall health
- Versions running
- etcd cluster status
- Any recent errors in logs
```

### 2. Investigating High Resource Usage

```
Show me the dashboard for my cluster, then identify which nodes
have high CPU or memory usage, and get the logs from the top 
resource consumers
```

### 3. Preparing for Maintenance

```
Before I perform maintenance on node 192.168.1.10:
1. Check its current health status
2. Show me what services are running
3. Verify it's not the only etcd member
4. List any important processes
```

### 4. Post-Deployment Verification

```
After deploying my Talos cluster:
1. Verify all nodes are healthy
2. Check that etcd has the correct number of members
3. Ensure kubelet is running on all nodes
4. Get the kubeconfig so I can access Kubernetes
```

### 5. Troubleshooting Network Issues

```
I'm having network issues on node 192.168.1.10. Can you:
1. Check the network configuration
2. Look at the networkd logs
3. Show me the current network interfaces
4. Read the resolv.conf file
```

## Advanced Examples

### Using Different Output Formats

```
Get services in JSON format
```

```
Show me members in YAML format
```

### Working with Multiple Nodes

```
Get the disk list from nodes 192.168.1.10,192.168.1.11,192.168.1.12
```

### Filtering Logs

```
Show me the last 50 lines of logs from the etcd service on my control plane
```

### Deep System Inspection

```
List all files in /dev on node 192.168.1.10 with depth 2
```

```
Read the kernel log from node 192.168.1.10
```

## Integration with Other MCP Servers

If you have other MCP servers configured (like filesystem or git), you can combine them:

```
Check my Talos cluster health and save the output to a file in my reports directory
```

```
Get the cluster configuration and commit it to my infrastructure git repository
```

## Error Handling

If Claude encounters an error, it will show you the error message. Common issues:

**Connection refused:**
```
Error: connection refused
```
Solution: Check that your endpoints are correct and the cluster is accessible.

**Authentication failed:**
```
Error: authentication failed
```
Solution: Verify your talosconfig has valid certificates.

**Node not found:**
```
Error: node not found
```
Solution: Check the node IP address is correct and the node is running.

## Best Practices

1. **Always specify node IPs** when working with specific nodes
2. **Use health checks** before performing operations
3. **Check logs** when troubleshooting issues
4. **Verify configuration** before making changes
5. **Keep your talosconfig secure** and up to date

## Getting Help

If you're unsure about what you can do:

```
What can you help me with regarding my Talos cluster?
```

```
What information can you get from my Talos nodes?
```

```
Show me examples of what I can ask about my Talos cluster
```
