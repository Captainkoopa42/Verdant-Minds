import networkx as nx
import numpy as np
import time
from typing import Dict, List, Tuple, Any, Optional

class MemoryWeb:
    """
    Associative memory system using a graph-based representation.
    Enables dynamic, associative linkage of concepts with stability
    and spread activation mechanisms.
    """
    
    def __init__(self):
        """Initialize the Memory Web."""
        self.graph = nx.Graph()
        self.memory_store = {}
        self.thought_clusters = {}
        self.activation_history = {}
        
        # Memory performance metrics
        self.metrics = {
            "total_concepts": 0,
            "total_connections": 0,
            "avg_stability": 0.0,
            "created_timestamp": time.time(),
            "last_access_timestamp": time.time()
        }
    
    def add_thought(self, label: str, stability: float = 0.5, metadata: Dict[str, Any] = None):
        """
        Add a concept to memory with specified stability.
        
        Args:
            label: Concept label/name
            stability: Initial concept stability (0-1)
            metadata: Additional concept metadata
        """
        if label not in self.memory_store:
            # Create new concept entry
            self.memory_store[label] = {
                "stability": stability,
                "connections": [],
                "first_seen": time.time(),
                "last_accessed": time.time(),
                "access_count": 1
            }
            
            # Add metadata if provided
            if metadata:
                self.memory_store[label]["metadata"] = metadata
            
            # Add to graph
            self.graph.add_node(label, stability=stability)
            
            # Connect to most stable existing thoughts for initial integration
            if len(self.memory_store) > 1:
                sorted_thoughts = sorted(
                    (thought for thought in self.memory_store.keys() if thought != label),
                    key=lambda x: self.memory_store[x]["stability"],
                    reverse=True
                )[:3]  # Connect to top 3 stable thoughts

                for conn in sorted_thoughts:
                    self.connect_thoughts(label, conn)
            
            # Update metrics
            self.metrics["total_concepts"] += 1
            
        else:
            # Update existing thought
            self.memory_store[label]["last_accessed"] = time.time()
            self.memory_store[label]["access_count"] += 1
            
            # Slightly reinforce existing memory
            old_stability = self.memory_store[label]["stability"]
            new_stability = min(1.0, old_stability + 0.02)
            self.memory_store[label]["stability"] = new_stability
            
            # Update metadata if provided
            if metadata and "metadata" in self.memory_store[label]:
                self.memory_store[label]["metadata"].update(metadata)
            elif metadata:
                self.memory_store[label]["metadata"] = metadata
        
        # Update last access time
        self.metrics["last_access_timestamp"] = time.time()
    
    def connect_thoughts(self, label1: str, label2: str, initial_weight: float = 0.5) -> bool:
        """
        Links two thoughts together with a dynamic connection weight.
        
        Args:
            label1: First concept label
            label2: Second concept label
            initial_weight: Initial connection weight
        
        Returns:
            True if a new connection was created, False if updated
        """
        if label1 not in self.memory_store or label2 not in self.memory_store:
            return False

        # Avoid creating self-referential connections
        if label1 == label2:
            return False
        
        # Calculate weight based on stability of both concepts
        weight = min(1.0, initial_weight * 
                     (self.memory_store[label1]["stability"] + 
                      self.memory_store[label2]["stability"]) / 2)
        
        # Check if connection already exists
        new_connection = True
        
        # Update connections in memory store
        if label2 not in [conn[0] for conn in self.memory_store[label1]["connections"]]:
            self.memory_store[label1]["connections"].append((label2, weight))
        else:
            new_connection = False
            # Update existing connection
            for i, (conn, existing_weight) in enumerate(self.memory_store[label1]["connections"]):
                if conn == label2:
                    # Blend weights
                    new_weight = existing_weight * 0.7 + weight * 0.3
                    self.memory_store[label1]["connections"][i] = (conn, new_weight)
                    break
                    
        if label1 not in [conn[0] for conn in self.memory_store[label2]["connections"]]:
            self.memory_store[label2]["connections"].append((label1, weight))
        else:
            # Update existing connection
            for i, (conn, existing_weight) in enumerate(self.memory_store[label2]["connections"]):
                if conn == label1:
                    # Blend weights
                    new_weight = existing_weight * 0.7 + weight * 0.3
                    self.memory_store[label2]["connections"][i] = (conn, new_weight)
                    break
        
        # Add or update edge in graph
        if self.graph.has_edge(label1, label2):
            current_weight = self.graph.get_edge_data(label1, label2)["weight"]
            new_weight = current_weight * 0.7 + weight * 0.3
            self.graph[label1][label2]["weight"] = new_weight
        else:
            self.graph.add_edge(label1, label2, weight=weight)
            self.metrics["total_connections"] += 1
            
        # Update metrics
        self.metrics["last_access_timestamp"] = time.time()
        self._update_average_stability()
            
        return new_connection
    
    def retrieve_related_thoughts(self, label: str, depth: int = 2, limit: int = 10) -> List[Tuple[str, float]]:
        """
        Gets related thoughts based on graph connectivity.
        
        Args:
            label: Concept label to start from
            depth: Search depth (hops in graph)
            limit: Maximum number of results
            
        Returns:
            List of (concept, relevance) tuples
        """
        if label not in self.memory_store:
            return []
        
        related_thoughts = []
        
        if label in self.graph:
            # Get subgraph of neighbors up to specified depth
            subgraph = nx.ego_graph(self.graph, label, radius=depth)
            
            # Convert to list of (thought, relevance) tuples
            for node in subgraph.nodes():
                if node != label:
                    # Calculate relevance based on path length and node stability
                    path_length = nx.shortest_path_length(subgraph, source=label, target=node)
                    stability = self.memory_store.get(node, {}).get("stability", 0.5)
                    
                    # Higher stability, shorter path = more relevant
                    relevance = stability / (path_length + 1)
                    related_thoughts.append((node, relevance))
        
        # Sort by relevance and limit results
        related_thoughts.sort(key=lambda x: x[1], reverse=True)
        
        # Update access time for retrieved concepts
        current_time = time.time()
        for concept, _ in related_thoughts[:limit]:
            if concept in self.memory_store:
                self.memory_store[concept]["last_accessed"] = current_time
                self.memory_store[concept]["access_count"] += 1
        
        self.metrics["last_access_timestamp"] = current_time
        
        return related_thoughts[:limit]
    
    def activate_concepts(self, seed_concepts: List[str], activation_strength: float = 0.7, 
                         spread_factor: float = 0.5) -> Dict[str, float]:
        """
        Perform spreading activation from seed concepts.
        
        Args:
            seed_concepts: Initial concepts to activate
            activation_strength: Initial activation strength
            spread_factor: How much activation spreads (0-1)
            
        Returns:
            Dictionary mapping concepts to activation levels
        """
        activations = {}
        visited = set()
        
        # Queue with (concept, activation_level, depth)
        queue = [(concept, activation_strength, 0) for concept in seed_concepts]
        
        # Arbitrary limits to prevent excessive spread
        max_depth = 3
        activation_threshold = 0.1
        
        while queue:
            concept, activation, depth = queue.pop(0)
            
            # Skip if already processed or below threshold
            if concept in visited or activation < activation_threshold:
                continue
                
            # Skip if depth too high
            if depth > max_depth:
                continue
                
            # Add to visited
            visited.add(concept)
            
            # Update activation (keep maximum if already activated)
            if concept in activations:
                activations[concept] = max(activations[concept], activation)
            else:
                activations[concept] = activation
                
            # Skip spread if concept not in memory
            if concept not in self.memory_store:
                continue
                
            # Get connections
            connections = self.memory_store[concept]["connections"]
            
            # Spread activation to neighbors
            for neighbor, weight in connections:
                # New activation = current * connection_weight * spread_factor
                new_activation = activation * weight * spread_factor
                
                # Add to queue
                queue.append((neighbor, new_activation, depth + 1))
        
        # Track activation history
        timestamp = time.time()
        for concept, activation in activations.items():
            if concept not in self.activation_history:
                self.activation_history[concept] = []
            
            self.activation_history[concept].append((timestamp, activation))
            
            # Keep history at reasonable size
            if len(self.activation_history[concept]) > 100:
                self.activation_history[concept] = self.activation_history[concept][-100:]
        
        return activations
    
    def cluster_thoughts(self, algorithm: str = 'louvain', min_stability: float = 0.3) -> Dict[str, List[str]]:
        """
        Cluster concepts in the memory web.
        
        Args:
            algorithm: Clustering algorithm ('louvain' or 'label_propagation')
            min_stability: Minimum concept stability to include
            
        Returns:
            Dictionary mapping cluster IDs to concept lists
        """
        # Filter nodes by stability
        stable_nodes = [
            node for node in self.graph.nodes() 
            if self.memory_store.get(node, {}).get("stability", 0) >= min_stability
        ]
        
        subgraph = self.graph.subgraph(stable_nodes)
        
        # Cannot cluster empty graph
        if not subgraph.nodes():
            return {}
        
        # Apply clustering algorithm
        if algorithm == 'louvain':
            try:
                from community import best_partition
                partition = best_partition(subgraph)
            except ImportError:
                # Fallback to networkx communities
                partition = self._fallback_clustering(subgraph)
        elif algorithm == 'label_propagation':
            partition = {}
            # Convert node labels to integers for algorithm
            node_map = {node: i for i, node in enumerate(subgraph.nodes())}
            reverse_map = {i: node for node, i in node_map.items()}
            
            # Create integer graph
            int_graph = nx.Graph()
            for u, v, data in subgraph.edges(data=True):
                int_graph.add_edge(node_map[u], node_map[v], weight=data.get('weight', 1.0))
                
            # Apply label propagation
            try:
                from networkx.algorithms.community import label_propagation_communities
                communities = label_propagation_communities(int_graph)
                
                # Convert back to original node labels
                for i, community in enumerate(communities):
                    for node_int in community:
                        partition[reverse_map[node_int]] = i
            except (ImportError, AttributeError):
                # Fallback to simpler algorithm
                partition = self._fallback_clustering(subgraph)
        else:
            # Default to fallback
            partition = self._fallback_clustering(subgraph)
        
        # Convert partition to clusters
        clusters = {}
        for node, cluster_id in partition.items():
            cluster_key = str(cluster_id)
            if cluster_key not in clusters:
                clusters[cluster_key] = []
            clusters[cluster_key].append(node)
        
        # Update stored clusters
        self.thought_clusters = clusters
        
        return clusters
    
    def _fallback_clustering(self, graph):
        """Simple fallback clustering when community detection algorithms are unavailable."""
        # Use a basic connected components approach
        components = list(nx.connected_components(graph))
        partition = {}
        
        for i, component in enumerate(components):
            for node in component:
                partition[node] = i
                
        return partition
    
    def reinforce_memory(self, label: str, amount: float = 0.1) -> float:
        """
        Reinforce a specific memory concept.
        
        Args:
            label: Concept to reinforce
            amount: Reinforcement amount (0-1)
            
        Returns:
            New stability value
        """
        if label not in self.memory_store:
            return 0.0
            
        # Get current stability
        current_stability = self.memory_store[label]["stability"]
        
        # Apply reinforcement
        new_stability = min(1.0, current_stability + amount)
        self.memory_store[label]["stability"] = new_stability
        
        # Update node properties in graph
        if label in self.graph:
            self.graph.nodes[label]["stability"] = new_stability
            
        # Update metrics
        self.metrics["last_access_timestamp"] = time.time()
        self._update_average_stability()
        
        return new_stability
    
    def decay_memories(self, decay_factor: float = 0.01, time_threshold: float = 86400) -> int:
        """
        Apply decay to memories not accessed recently.
        
        Args:
            decay_factor: Amount to decay stability
            time_threshold: Time in seconds (default: 1 day)
            
        Returns:
            Number of concepts affected
        """
        current_time = time.time()
        affected_count = 0
        
        for concept, data in self.memory_store.items():
            last_accessed = data.get("last_accessed", 0)
            
            # Apply decay to concepts not accessed recently
            if current_time - last_accessed > time_threshold:
                old_stability = data["stability"]
                new_stability = max(0.1, old_stability - decay_factor)
                
                # Update stability
                data["stability"] = new_stability
                
                # Update node properties in graph
                if concept in self.graph:
                    self.graph.nodes[concept]["stability"] = new_stability
                    
                affected_count += 1
        
        # Update metrics
        if affected_count > 0:
            self._update_average_stability()
            
        return affected_count
    
    def get_concept_details(self, label: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a concept.
        
        Args:
            label: Concept label
            
        Returns:
            Dictionary with concept details or None if not found
        """
        if label not in self.memory_store:
            return None
            
        # Create copy of memory data
        concept_data = dict(self.memory_store[label])
        
        # Add graph-specific metrics
        if label in self.graph:
            # Add degree (number of connections)
            concept_data["degree"] = self.graph.degree[label]
            
            # Add centrality score
            try:
                centralities = nx.closeness_centrality(self.graph)
                concept_data["centrality"] = centralities.get(label, 0)
            except:
                concept_data["centrality"] = 0
            
        # Add cluster membership
        for cluster_id, members in self.thought_clusters.items():
            if label in members:
                concept_data["cluster"] = cluster_id
                break
                
        return concept_data
    
    def _update_average_stability(self):
        """Update average stability metric."""
        if not self.memory_store:
            self.metrics["avg_stability"] = 0.0
            return
            
        total_stability = sum(data["stability"] for data in self.memory_store.values())
        self.metrics["avg_stability"] = total_stability / len(self.memory_store)
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get memory web performance metrics.
        
        Returns:
            Dictionary of metrics
        """
        # Update metrics
        self.metrics["total_concepts"] = len(self.memory_store)
        self.metrics["total_connections"] = self.graph.number_of_edges()
        self._update_average_stability()
        
        # Add additional metrics for more comprehensive reporting
        active_concepts = sum(1 for data in self.memory_store.values() 
                             if time.time() - data.get("last_accessed", 0) < 86400)  # Active in last day
        
        # Calculate network metrics if graph is non-empty
        network_metrics = {}
        if self.graph.number_of_nodes() > 0:
            try:
                # Average degree
                degrees = [d for _, d in self.graph.degree()]
                avg_degree = sum(degrees) / max(1, len(degrees))
                network_metrics["avg_degree"] = avg_degree
                
                # Graph density
                network_metrics["graph_density"] = nx.density(self.graph)
                
                # Number of clusters
                network_metrics["cluster_count"] = len(self.thought_clusters)
                
                # Calculate largest cluster size
                if self.thought_clusters:
                    largest_cluster = max(self.thought_clusters.values(), key=len)
                    network_metrics["largest_cluster_size"] = len(largest_cluster)
            except Exception as e:
                # Fallback if network analysis fails
                network_metrics["error"] = str(e)
        
        # Add activation metrics
        activation_metrics = {
            "total_activations": sum(len(history) for history in self.activation_history.values()),
            "active_concepts_count": active_concepts,
            "active_concepts_ratio": active_concepts / max(1, len(self.memory_store))
        }
        
        # Time-based metrics
        time_metrics = {
            "age_seconds": time.time() - self.metrics["created_timestamp"],
            "time_since_last_access": time.time() - self.metrics["last_access_timestamp"]
        }
        
        # Combine all metrics
        return {
            **self.metrics,
            **network_metrics,
            **activation_metrics,
            **time_metrics
        }