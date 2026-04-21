import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

import pygame
import json
import math
from collections import deque
from entities.ambulance import Ambulance
from pathfinding.mapping import dijkstra
from entities.patients import Patient
from scheduling.scheduler import Scheduler

# ---------------- CONFIG ----------------
WINDOW_WIDTH, WINDOW_HEIGHT = 1500, 768
PANEL_WIDTH = 400
GRAPH_WIDTH = WINDOW_WIDTH - PANEL_WIDTH
NODE_RADIUS = 15
AMB_RADIUS = 12
HOSPITAL_NODE = '0'
FPS = 60
SIMULATION_STARTED = False
SIMULATION_RUNNING = False
SIMULATION_DONE = False
SELECTED_ALGO = "FCFS" # just default
SHOW_METRICS = False
METRICS_READY = False

patients = []
patient_map = {}
scheduler = None
schedule_results = []
current_step = 0
log_scroll = 0
node_states = {}
metrics_data = {}
dispatched_ids= set()


# Colors
BG_COLOR = (18, 18, 24)
NODE_COLOR = (52, 152, 219)
HOVER_COLOR = (241, 196, 15)
HOSPITAL_COLOR = (231, 76, 60)
EDGE_COLOR = (80, 80, 100)
AMB_IDLE_COLOR = (46, 204, 113)
AMB_MOVING_COLOR = (52, 152, 219)
SIREN_COLOR = (255, 80, 80)
TEXT_COLOR = (255, 255, 255)
PANEL_BG = (30, 30, 40, 220)

# start button
START_BUTTON_RECT = pygame.Rect(20, 20, 180, 50)
BUTTON_COLOR = (46, 204, 113)
BUTTON_HOVER = (39, 174, 96)
BUTTON_TEXT_COLOR = (0, 0, 0)

# show result button
RESULT_BUTTON_RECT = pygame.Rect(220, 20, 180, 50)

# ---------------- LOAD GRAPH ----------------
with open(resource_path("data/graph.json")) as f:
    raw_graph = json.load(f)

# normalize all keys and neighbors to strings
graph = {str(node): [(str(nbr), w) for nbr, w in neighbors] 
         for node, neighbors in raw_graph.items()}

if HOSPITAL_NODE not in graph:
    raise ValueError(f"Hospital node '{HOSPITAL_NODE}' not found in graph.")

nodes = list(graph.keys())
edges = []
for u in graph:
    for v, w in graph[u]:
        if (v, u) not in [(e[1], e[0]) for e in edges]:
            edges.append((u, v, w))

# ---------------- NODE POSITIONS ----------------
with open(resource_path("data/positions.json")) as f:
    positions = json.load(f)

# Convert lists → tuples (important for pygame)
positions = {k: tuple(v) for k, v in positions.items()}

positions[HOSPITAL_NODE] = positions[HOSPITAL_NODE]  # ensure hospital is in positions


# ---------------- NORMALIZE & CENTER POSITIONS ----------------
# Get bounds
xs = [pos[0] for pos in positions.values()]
ys = [pos[1] for pos in positions.values()]

min_x, max_x = min(xs), max(xs)
min_y, max_y = min(ys), max(ys)

graph_width = max_x - min_x
graph_height = max_y - min_y

# Compute scale (fit inside window with margin)
margin = 100
scale_x = (GRAPH_WIDTH - margin) / graph_width
scale_y = (WINDOW_HEIGHT - margin) / graph_height
scale = min(scale_x, scale_y)

# Center offset
offset_x = (GRAPH_WIDTH - graph_width * scale) / 2
offset_y = (WINDOW_HEIGHT - graph_height * scale) / 2

# Apply transformation
positions = {
    node: (
        (x - min_x) * scale + offset_x,
        (y - min_y) * scale + offset_y
    )
    for node, (x, y) in positions.items()
}

# ---------------- HELPERS ----------------
def get_current_node(amb):
    """Return the nearest node to the ambulance."""
    closest, min_dist = None, float('inf')
    for node, pos in positions.items():
        d = math.hypot(pos[0]-amb.x, pos[1]-amb.y)
        if d < min_dist:
            min_dist = d
            closest = node
    return closest if min_dist < NODE_RADIUS*2 else None

def wrap_text(text, font, max_width):
    words = text.split(' ')
    lines = []
    current_line = ""

    for word in words:
        test_line = current_line + word + " "
        if font.size(test_line)[0] <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word + " "

    lines.append(current_line)
    return lines

# def get_active_paths():
#     paths = []

#     for amb in ambulances:
#         if amb.state == "TO_PATIENT":
#             paths.append((amb.path, (255, 0, 0)))  # RED

#         elif amb.state == "SERVICING":
#             paths.append((amb.path, (255, 255, 0)))  # YELLOW

#         elif amb.state == "RETURNING":
#             paths.append((amb.path, (0, 255, 0)))  # GREEN

#     return paths

# ---------------- DISPATCH SYSTEM ----------------
class DispatchSystem:
    def __init__(self, ambulances, patient_amp):
        self.ambulances = ambulances
        self.patient_map = patient_map
        self.node_states = {}
        self.status = {amb: "idle" for amb in ambulances}
        self.dest_node = {amb: None for amb in ambulances}
        self.log = deque()

        self.patient_map = patient_map or {}

    def get_nearest_idle_ambulance(self, target):
        best_amb, best_dist = None, float('inf')

        for amb in self.ambulances:
            # MUST be idle AND at hospital
            if amb.state != "IDLE":
                continue

            if str(amb.location) != str(HOSPITAL_NODE):
                continue  # not yet returned to hospital

            path, dist = dijkstra(graph, amb.location, target)

            if dist < best_dist:
                best_dist = dist
                best_amb = amb

        return best_amb

    def dispatch(self, amb, patient_node, sim_time):
        amb.target_node = patient_node
        patient = self.patient_map[str(patient_node)]

        self.node_states[str(patient.id)] = "WAITING"
        
        hospital_node = HOSPITAL_NODE

        start_node = get_current_node(amb)

        if not start_node or start_node not in graph or patient_node not in graph:
            self.log.appendleft(f"Amb {amb.id + 1} | FAILED")
            return False

        travel_info = amb.dispatch(graph, patient_node, hospital_node)

        path_to_patient = travel_info["to_patient_path"]
        path_back = travel_info["to_hospital_path"]

        # where state belongs
        amb.state = "TO_PATIENT"
        amb.service_time = patient.service_time
        amb.patient_id = patient.id
        amb.return_path = path_back

        amb.set_path(path_to_patient)

        self.status[amb] = "enroute"
        self.dest_node[amb] = patient_node

        self.add_log(
            sim_time,
            "DISPATCH",
            f"Amb {amb.id+1} → P{patient.id}",
            patient
        )

        return True
    
    def add_log(self, sim_time, event, details="", patient=None):
        msg = f"[t={sim_time:.2f}] {event}"

        if patient:
            msg += f" | P{patient.id} | AT={patient.arrival_time} | ST={patient.service_time}"

        if details:
            msg += f" | {details}"

        self.log.appendleft(msg)

    def update(self):
        for amb in self.ambulances:

            # Update status based on state
            if amb.state in ["TO_PATIENT", "RETURNING"]:
                self.status[amb] = "enroute"

            elif amb.state == "SERVICING":
                self.status[amb] = "servicing"

            elif amb.state == "IDLE":
                self.status[amb] = "idle"

            # Detect arrival at hospital (END of RETURNING) 
            if amb.state == "RETURNING" and not amb.moving:
                amb.state = "IDLE"
                self.dest_node[amb] = None

                # self.log.appendleft(
                #     f"Amb {amb.id} READY at hospital"
                # )

    def get_ambulance_color(self, amb):
        if amb.state == "TO_PATIENT":
            return (255, 0, 0)       # RED
        elif amb.state == "SERVICING":
            return (255, 255, 0)     # YELLOW
        elif amb.state == "RETURNING":
            return (0, 255, 0)       # GREEN
        else:
            return AMB_IDLE_COLOR

# ---------------- PYGAME ----------------
pygame.init()
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("PulsePoint-inator")
clock = pygame.time.Clock()
font = pygame.font.SysFont("segoeui", 16)

ambulances = [Ambulance(i, HOSPITAL_NODE, positions, speed=150) for i in range(5)]
dispatch_sys = DispatchSystem(ambulances, patient_map)

for amb in ambulances:
    amb.node_states = dispatch_sys.node_states

hovered_node = None
hover_path = []

# ---------------- DRAW ----------------
def draw_graph(highlight=None):
    # draw edges
    for u, v, _ in edges:
        pygame.draw.line(screen, (255, 255, 255), positions[u], positions[v], 2)

    # draw nodes
    for node, pos in positions.items():

        state = dispatch_sys.node_states.get(node)

        color = NODE_COLOR  # default first

        if state == "WAITING":
            color = (255, 0, 0)

        elif state == "SERVICING":
            color = (255, 255, 0)

        elif state == "DONE":
            color = (0, 255, 0)

        if node == HOSPITAL_NODE:
            color = HOSPITAL_COLOR

        if node == highlight:
            color = HOVER_COLOR

        pygame.draw.circle(screen, color, pos, NODE_RADIUS)
        text = font.render(node, True, TEXT_COLOR)
        rect = text.get_rect(center=(pos[0], pos[1]))
        screen.blit(text, rect)

def draw_ambulances(siren=False):
    for amb in ambulances:
        color = SIREN_COLOR if amb.state != "IDLE" and siren else (AMB_MOVING_COLOR if amb.moving else AMB_IDLE_COLOR)
        pygame.draw.circle(screen, dispatch_sys.get_ambulance_color(amb), (int(amb.x), int(amb.y)), AMB_RADIUS)

def draw_panel():
    panel = pygame.Surface((PANEL_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
    panel.fill(PANEL_BG)
    y = 20
    panel.blit(font.render("Dispatch Status", True, TEXT_COLOR), (10, y))
    y += 40
    for amb in ambulances:
        dest = dispatch_sys.dest_node[amb]
        state = amb.state

        # Color based on REAL state
        if state == "IDLE":
            color = AMB_IDLE_COLOR
        elif state == "TO_PATIENT":
            color = (255, 0, 0)       # RED
        elif state == "SERVICING":
            color = (255, 255, 0)     # YELLOW
        elif state == "RETURNING":
            color = (0, 255, 0)       # GREEN
        else:
            color = AMB_IDLE_COLOR

        pygame.draw.circle(panel, color, (15, y+8), 8)

        # Display readable label
        panel.blit(
            font.render(f"Ambulance {amb.id + 1}: {state}", True, TEXT_COLOR),
            (30, y)
        )
        
        if dest:
            panel.blit(font.render(f"{dest}", True, TEXT_COLOR), (30, y+20))
        y += 50
    panel.blit(font.render("Log:", True, TEXT_COLOR), (10, y))
    y += 25
    panel.blit(font.render(f"Algorithm: {SELECTED_ALGO}", True, TEXT_COLOR), (10, y))
    y += 30
    
    LOG_START_Y = y + 5
    LOG_END_Y = WINDOW_HEIGHT - 20

    log_rect = pygame.Rect(0, LOG_START_Y, 400, LOG_END_Y - LOG_START_Y)

    panel.set_clip(log_rect)
    
    y_log = y + log_scroll
    max_width = 350  # panel width minus padding

    for entry in dispatch_sys.log:
        wrapped_lines = wrap_text(entry, font, max_width)

        for line in wrapped_lines:
            panel.blit(font.render(line, True, TEXT_COLOR), (10, y_log))
            y_log += 20
    panel.set_clip(None)

    screen.blit(panel, (GRAPH_WIDTH, 0))

def draw_start_button(mouse_pos):

    if SIMULATION_RUNNING:
        color = (120, 120, 120)
    else:
        color = BUTTON_HOVER if START_BUTTON_RECT.collidepoint(mouse_pos) else BUTTON_COLOR

    pygame.draw.rect(screen, color, START_BUTTON_RECT, border_radius=10)

    # 👇 THIS is your requirement
    if SIMULATION_DONE:
        label = "RESTART"
    else:
        label = "START"

    text = font.render(label, True, BUTTON_TEXT_COLOR)
    rect = text.get_rect(center=START_BUTTON_RECT.center)
    screen.blit(text, rect)

def reset_simulation():
    global SIMULATION_RUNNING, schedule_results, current_step
    global node_states, sim_time

    SIMULATION_RUNNING = False
    schedule_results = []
    current_step = 0
    sim_time = 0

    dispatch_sys.node_states.clear()

    for amb in ambulances:
        amb.location = HOSPITAL_NODE
        amb.x, amb.y = positions[HOSPITAL_NODE]
        amb.moving = False
        amb.path = []
        amb.busy_until = 0

def draw_metrics_popup(screen, font, metrics):
    popup = pygame.Surface((520, 500))
    popup.fill((20, 20, 30))

    # border
    pygame.draw.rect(popup, (100, 100, 140), popup.get_rect(), 2)

    y = 25
    spacing = 30

    title_font = pygame.font.SysFont("segoeui", 20, bold=True)

    title = title_font.render("SIMULATION RESULTS", True, (255, 255, 255))
    popup.blit(title, (160, y))
    y += 50

    lines = [
        f"Algorithm: {metrics['algo']}",
        f"Patients Served: {metrics['count']}",
        "",
        f"Average Waiting Time: {metrics['avg_wait']:.2f}",
        f"Maximum Waiting Time: {metrics['max_wait']:.2f}",
        f"Minimum Waiting Time: {metrics['min_wait']:.2f}",
        "",
        f"Average Turnaround Time: {metrics['avg_turn']:.2f}",
        f"Total Simulation Time: {metrics['total_time']:.2f}",
        "",
        f"Throughput: {metrics['throughput']:.3f} patients/unit time",
        "",
        "Press R to reset"
    ]

    for line in lines:
        text = font.render(line, True, (220, 220, 220))
        popup.blit(text, (40, y))
        y += spacing

    screen.blit(popup, (GRAPH_WIDTH//2 - 260, WINDOW_HEIGHT//2 - 180))

def draw_result_button(mouse_pos):
    if not SIMULATION_DONE:
        return

    color = BUTTON_HOVER if RESULT_BUTTON_RECT.collidepoint(mouse_pos) else BUTTON_COLOR
    pygame.draw.rect(screen, color, RESULT_BUTTON_RECT, border_radius=10)

    text = font.render("RESULTS", True, BUTTON_TEXT_COLOR)
    rect = text.get_rect(center=RESULT_BUTTON_RECT.center)
    screen.blit(text, rect)



# ---------------- MAIN LOOP ----------------
running = True
siren_timer = 0
sim_time = 0
while running:
    dt = clock.tick(FPS)/600
    sim_time += dt
    siren_timer = (siren_timer + dt) % 0.5
    siren_on = siren_timer < 0.25

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not SIMULATION_RUNNING:
            mx, my = pygame.mouse.get_pos()
            
            if RESULT_BUTTON_RECT.collidepoint(mx, my) and SIMULATION_DONE:
                SHOW_METRICS = True
           

            if START_BUTTON_RECT.collidepoint(mx, my):

                # IF SIMULATION ALREADY DONE → THIS IS RESTART
                if SIMULATION_DONE:
                    reset_simulation()
                    dispatch_sys.log.clear()  # clear logs
                    dispatched_ids.clear()
                    sim_time = 0
                    SIMULATION_DONE = False
                    METRICS_READY = False
                    SHOW_METRICS = False

                    dispatch_sys.log.appendleft("Simulation restarted.")
                else:
                    dispatch_sys.log.appendleft("Simulation started.")

                patients = Patient.get_patients(graph, HOSPITAL_NODE)

                patient_map = {str(p.id): p for p in patients}
                dispatch_sys.patient_map = patient_map

                for p in patients:
                    node_states[str(p.id)] = "WAITING"

                scheduler = Scheduler(patients, ambulances, HOSPITAL_NODE, graph)

                if SELECTED_ALGO == "FCFS":
                    schedule_results = scheduler.fcfs()
                elif SELECTED_ALGO == "SJF":
                    schedule_results = scheduler.sjf()
                elif SELECTED_ALGO == "HRRN":
                    schedule_results = scheduler.hrrn()

                SIMULATION_RUNNING = True
                current_step = 0

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_1:
                SELECTED_ALGO = "FCFS"
            elif event.key == pygame.K_2:
                SELECTED_ALGO = "SJF"
            elif event.key == pygame.K_3:
                SELECTED_ALGO = "HRRN"
            # alternative for restart button
            elif event.key == pygame.K_r:
                if SIMULATION_DONE:
                    reset_simulation()
                    dispatch_sys.log.clear()
                    dispatched_ids.clear()
                    sim_time = 0
                    SIMULATION_DONE = False
                    METRICS_READY = False
                    SHOW_METRICS = False

                    dispatch_sys.log.appendleft("Simulation restarted.")


        elif event.type == pygame.MOUSEWHEEL:
            log_scroll += event.y * 20
            log_scroll = max(-3000, min(0, log_scroll))


    if SIMULATION_RUNNING and not SIMULATION_DONE:

        all_idle = all(amb.state == "IDLE" for amb in ambulances)
        all_done = current_step >= len(schedule_results)

        if all_done and all_idle:
            SIMULATION_DONE = True
            SIMULATION_RUNNING = False

            metrics_data = Scheduler.compute_metrics(schedule_results)
            metrics_data["algo"] = SELECTED_ALGO

            METRICS_READY = True

            #if not SIMULATION_DONE:
            dispatch_sys.log.appendleft("Simulation Completed.")
            dispatch_sys.log.appendleft("All emergencies handled successfully.")


    

    if SIMULATION_RUNNING and current_step < len(schedule_results):
        result = schedule_results[current_step]
        patient = patient_map[str(result["patient_id"])]

        patient_node = str(patient.id)
        
        # USE dispatch_time from scheduler
        if sim_time >= result["dispatch_time"] and result["patient_id"] not in dispatched_ids:

            amb = dispatch_sys.get_nearest_idle_ambulance(patient_node)

            if amb:
                dispatch_sys.dispatch(amb, patient_node, sim_time)

                dispatched_ids.add(result["patient_id"])

                current_step += 1



    # hovered_node = None
    # hover_path = []
    # mx, my = pygame.mouse.get_pos()
    # for node, pos in positions.items():
    #     if math.hypot(mx-pos[0], my-pos[1]) < NODE_RADIUS+5:
    #         hovered_node = node
    #         amb = dispatch_sys.get_nearest_idle_ambulance(node)
    #         start = get_current_node(amb) if amb else None
    #         if start and start in graph and node in graph:
    #             hover_path, _ = dijkstra(graph, start, node)
    #         break

    for amb in ambulances:
        amb.update(dt, sim_time, dispatch_sys)
    dispatch_sys.update()

    screen.fill(BG_COLOR)
    draw_graph(highlight=hovered_node)
    draw_ambulances(siren_on)
    draw_panel()
    mouse_pos = pygame.mouse.get_pos()
    draw_start_button(mouse_pos)   
    draw_result_button(mouse_pos)

    if SHOW_METRICS:
        draw_metrics_popup(screen, font, metrics_data)

    pygame.display.flip()

pygame.quit()


