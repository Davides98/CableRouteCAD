import math
import heapq
from PyQt6.QtWidgets import QGraphicsLineItem
from PyQt6.QtCore import QPointF, Qt

def get_node_key(x, y):
    return (round(x, 1), round(y, 1))

def build_routing_graph(items):
    """
    Builds a graph from QGraphicsLineItems in the list.
    Returns a dict: { (x,y): [(cost, (x,y)), ...] }
    """
    graph = {}
    lines = [i for i in items if isinstance(i, QGraphicsLineItem)]
    
    for line_item in lines:
        line = line_item.line()
        p1 = get_node_key(line.x1(), line.y1())
        p2 = get_node_key(line.x2(), line.y2())
        
        dist = line.length()
        
        if p1 not in graph: graph[p1] = []
        if p2 not in graph: graph[p2] = []
        
        graph[p1].append((dist, p2))
        graph[p2].append((dist, p1))
        
    return graph


def check_segregation(tray_service, cable_type):
    """
    Returns True if cable_type is allowed in tray_service.
    """
    ts = str(tray_service).strip().lower()
    ct = str(cable_type).strip().lower()
    
    # DEBUG: Only print if there is a mismatch to avoid flooding
    allowed = False
    if ts.startswith("mixed"):
        allowed = True
    else:
        allowed = (ts == ct)
    
    # print(f"DEBUG: Check Segregation: Tray='{ts}' Cable='{ct}' -> {allowed}")
    return allowed

def check_capacity(tray_capacity, current_load, cable_size):
    """
    Returns True if there is enough space.
    """
    return (current_load + cable_size) <= tray_capacity

def build_routing_graph(items):
    """
    Builds a graph from QGraphicsLineItems.
    Returns: { (x,y): [ (cost, neighbor_key, properties), ... ] }
    properties includes: service, capacity, current_load, id
    """
    graph = {}
    lines = [i for i in items if isinstance(i, QGraphicsLineItem)]
    
    for line_item in lines:
        line = line_item.line()
        p1 = get_node_key(line.x1(), line.y1())
        p2 = get_node_key(line.x2(), line.y2())
        
        dist = line.length()
        
        # Extract properties - SUPPORT LIST OF TRAYS
        tray_data = line_item.data(Qt.ItemDataRole.UserRole)
        
        trays_list = []
        if isinstance(tray_data, list):
             trays_list = tray_data # List of TrayInstance objects (or dicts)
        elif tray_data:
             trays_list = [tray_data] # Single object
        
        # We store the list of trays in props
        props = {
            "trays": trays_list # This will be used by astar
        }
        
        if p1 not in graph: graph[p1] = []
        if p2 not in graph: graph[p2] = []
        
        # Add edge with properties
        graph[p1].append((dist, p2, props))
        graph[p2].append((dist, p1, props))
        
    return graph

def project_point_on_segment(px, py, x1, y1, x2, y2):
    dx = x2 - x1
    dy = y2 - y1
    if dx == 0 and dy == 0:
        return x1, y1
        
    t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
    t = max(0, min(1, t))
    
    return x1 + t * dx, y1 + t * dy

def add_virtual_nodes(graph, points, lines):
    """
    Integrates points into the graph.
    NOTE: When splitting a segment, we must preserve its properties!
    """
    node_mapping = {} 
    
    for px, py in points:
        best_dist = float('inf')
        best_line = None
        best_proj = None
        
        for line_item in lines:
            line = line_item.line()
            lx1, ly1 = line.x1(), line.y1()
            lx2, ly2 = line.x2(), line.y2()
            
            proj_x, proj_y = project_point_on_segment(px, py, lx1, ly1, lx2, ly2)
            dist = math.hypot(px - proj_x, py - proj_y)
            
            if dist < best_dist:
                best_dist = dist
                best_line = line_item # Keep item to access data
                best_proj = (proj_x, proj_y)
        
        if best_line and best_proj:
            line_geom = best_line.line()
            u = get_node_key(line_geom.x1(), line_geom.y1())
            v = get_node_key(line_geom.x2(), line_geom.y2())
            p = get_node_key(best_proj[0], best_proj[1])
            
            if p == u:
                node_mapping[(px, py)] = u
                continue
            if p == v:
                node_mapping[(px, py)] = v
                continue
                
            # Get properties from the original line
            tray_data = best_line.data(Qt.ItemDataRole.UserRole)
            # Get properties from the original line - UPDATED FOR MULTI-TRAY
            tray_data = best_line.data(Qt.ItemDataRole.UserRole)
            
            trays_list = []
            if isinstance(tray_data, list):
                 trays_list = tray_data 
            elif tray_data:
                 trays_list = [tray_data]
            
            props = {
                "trays": trays_list
            }

            d_pu = math.hypot(p[0]-u[0], p[1]-u[1])
            d_pv = math.hypot(p[0]-v[0], p[1]-v[1])
            
            if p not in graph: graph[p] = []
            
            # Add connections with properties
            graph[p].append((d_pu, u, props))
            if u in graph: graph[u].append((d_pu, p, props))
            
            graph[p].append((d_pv, v, props))
            if v in graph: graph[v].append((d_pv, p, props))
            
            node_mapping[(px, py)] = p
            
    return node_mapping

def astar(graph, start, goal, cable_type="Power", cable_size=0):
    """
    A* Pathfinding with segregation and capacity checks.
    """
    if start not in graph or goal not in graph:
        return None

    open_set = []
    heapq.heappush(open_set, (0, start))
    
    came_from = {}
    g_score = {node: float('inf') for node in graph}
    g_score[start] = 0
    
    f_score = {node: float('inf') for node in graph}
    f_score[start] = math.hypot(start[0] - goal[0], start[1] - goal[1])
    
    while open_set:
        current = heapq.heappop(open_set)[1]
        
        if current == goal:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.append(start)
            return path[::-1]
            
        # Iterate neighbors. Structure: (dist, neighbor, properties)
        for dist, neighbor, props in graph.get(current, []):
            
            # --- CHECKS ---
            # Now we have a list of trays. We need to find AT LEAST ONE that fits.
            # props["trays"] is a list of TrayInstance objects (or dicts).
            
            trays = props.get("trays", [])
            valid_tray_found = False
            
            if not trays:
                # If no trays assigned, treat as generic cable tray with infinite capacity and universal compatibility
                # This allows routing to work on "raw" DXF imports without detailed config
                valid_tray_found = True
            else:
                for tray in trays:
                    # Normalize tray data access (obj vs dict)
                    t_service = "Unassigned"
                    t_capacity = 0
                    t_load = 0
                    
                    if hasattr(tray, 'service'):
                         t_service = tray.service
                         t_capacity = tray.capacity
                         t_load = tray.current_load
                         # Handle included services for Mixed trays
                         t_included = getattr(tray, 'included_services', [])
                         t_max_fill = getattr(tray, 'max_fill_percent', 80.0)
                    elif isinstance(tray, dict):
                         t_service = tray.get('service', 'Unassigned')
                         t_capacity = tray.get('capacity', 0)
                         t_load = tray.get('current_load', 0)
                         t_included = tray.get('included_services', [])
                         t_max_fill = tray.get('max_fill_percent', 80.0)
                    
                    # Apply Max Fill Limit
                    t_effective_capacity = t_capacity * (t_max_fill / 100.0)
                    
                    # Check Segregation
                    seg_ok = False
                    ts_norm = str(t_service).strip().lower()
                    ct_norm = str(cable_type).strip().lower()
                    
                    if ts_norm.startswith("mixed"):
                        # If mixed, check if cable type is in included_services
                        # If included_services is empty, traditionally Mixed allows all?
                        # User said: "dovranno essere rispettate le percentuali", meaning only defined types allowed.
                        # But also said: "nel caso esista una passerella Mixed...".
                        # Let's assume: if involved types are defined, check them.
                        if t_included:
                             # included_services might be list of dicts [{'name':'Power',...}] or strings
                             allowed_sub = []
                             for x in t_included:
                                 if isinstance(x, dict): allowed_sub.append(str(x.get('name','')).lower())
                                 elif isinstance(x, str): allowed_sub.append(str(x).lower())
                             
                             if ct_norm in allowed_sub:
                                 seg_ok = True
                             # Fallback: if user didn't define strict mixed list, but called it mixed?
                             # Let's be strict: if list exists, must match.
                             # If list empty, maybe allow all?
                             elif not allowed_sub:
                                 seg_ok = True 
                        else:
                             # No definition -> Allow all (Legacy Mixed behavior)
                             seg_ok = True
                    else:
                        # Direct match
                        if ts_norm == ct_norm:
                            seg_ok = True
                            
                    if not seg_ok: continue
                    
                    # Check Capacity (Effective)
                    if check_capacity(t_effective_capacity, t_load, cable_size):
                        valid_tray_found = True
                        break # Found one valid tray, edge is traversable
            
            if not valid_tray_found:
                continue
            # --------------
            
            tentative_g_score = g_score[current] + dist
            if tentative_g_score < g_score.get(neighbor, float('inf')):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g_score
                f = tentative_g_score + math.hypot(neighbor[0] - goal[0], neighbor[1] - goal[1])
                f_score[neighbor] = f
                heapq.heappush(open_set, (f, neighbor))
                
    return None # No path
