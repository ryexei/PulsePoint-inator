# PulsePoint-Inator: Ambulance Dispatch Simulation System

PulsePoint-Inator is a simulation system developed to evaluate emergency response efficiency using non-preemptive operating system scheduling algorithms. The system models ambulances as servers and patient requests as tasks, enabling a comparative analysis of dispatch strategies under conditions of uncertainty.

## Project Overview

In real-world emergency response systems, the severity of incidents is often unknown at the time of dispatch. This simulation addresses that limitation by assuming uniform severity across all emergencies while varying only the estimated service times. The system visualizes ambulance movement within a weighted graph network and evaluates how different scheduling algorithms affect system performance.

The simulation focuses on comparing scheduling strategies in terms of response efficiency, waiting time, turnaround time, and throughput.

## Key Features

- Implementation of scheduling algorithms: First Come, First Served (FCFS), Shortest Job First (SJF), and Highest Response Ratio Next (HRRN)
- Dijkstra’s Algorithm for shortest-path routing between hospital and patient nodes
- Real-time visualization of ambulance movement and system state using Pygame
- Automatic computation of performance metrics (waiting time, turnaround time, throughput)
- Graph-based environment with dynamically generated emergency requests

## Technical Stack

- Programming Language: Python  
- User Interface and Visualization: Pygame  
- Data Storage: JSON (graph structure and node positions)  
- Programming Paradigm: Object-Oriented Programming (OOP)  

## Algorithms Implemented

### Scheduling Algorithms

1. First Come, First Served (FCFS)  
   Processes requests based on arrival time. It is simple and fair but may result in longer average waiting times due to the convoy effect.

2. Shortest Job First (SJF)  
   Prioritizes requests with the shortest service time to minimize average waiting time. However, it may cause starvation of longer tasks.

3. Highest Response Ratio Next (HRRN)  
   Balances waiting time and service time by dynamically computing a response ratio. This prevents starvation while maintaining efficiency.

### Pathfinding Algorithm

- Dijkstra’s Algorithm  
  Used to compute the shortest path between the hospital and patient nodes in the weighted graph, ensuring optimal ambulance routing.

## System Components

The simulation consists of the following components:

- Nodes representing locations in the graph (hospital and patient request points)
- Weighted edges representing travel cost between locations
- Ambulances acting as servers that respond to patient requests
- Patients acting as tasks with randomly generated arrival times and service durations
- Scheduler module responsible for assigning ambulances using selected scheduling algorithms and computing performance metrics
- Pathfinding module implementing Dijkstra’s Algorithm for route optimization
- Logging system for tracking simulation events and dispatch history

The number of ambulances is fixed, while the number of patients, arrival times, and service durations are randomly generated per simulation run.

## Mechanics of the Simulation

The simulation operates on a graph-based environment where ambulances are dispatched from a central hospital node to patient nodes based on scheduling decisions.

### Simulation Process (Simplified)

1. Generate patient nodes with random arrival and service times
2. Load graph structure and node positions
3. Select scheduling algorithm (FCFS, SJF, or HRRN)
4. Dispatch ambulances based on scheduler output
5. Compute shortest paths using Dijkstra’s Algorithm
6. Simulate real-time ambulance movement
7. Track completion and compute performance metrics
8. Display results after simulation ends

### User Controls

- START button: Begins or restarts the simulation
- RESULTS button: Displays performance metrics after completion
- Keyboard shortcuts:
  - 1 → FCFS
  - 2 → SJF
  - 3 → HRRN
  - R → Reset simulation 

## Project Structure

The system follows a modular architecture:

AMBULANCE-DISPATCH-SIMULATION/
│
├── main.py                     # Core simulation loop and Pygame interface controller
├── .gitignore                 # Ignored files and build artifacts
│
├── data/                      # Graph and simulation data
│   ├── graph.json            # Weighted graph adjacency data
│   ├── positions.json        # Node coordinate positions for visualization
│   └── location_list.py      # Utility data / preprocessing reference
│
├── entities/                 # Core simulation objects
│   ├── ambulance.py          # Ambulance (server) behavior and movement logic
│   └── patients.py           # Patient (task) generation and attributes
│   
│
├── scheduling/               # Operating system scheduling algorithms
│   └── scheduler.py         # FCFS, SJF, HRRN implementation + metrics computation
│
├── pathfinding/             # Routing and navigation algorithms
│   └── mapping.py           # Dijkstra’s shortest path algorithm implementation
│
├── helpers/		     # Data parsing and conversion utilities
│   ├── list_to_perNode_parsing.py
│   ├── matrix_to_list_parsing.py
│   ├── network_svg.py
└─  └── svg_to_nodePos_extraction.py




## Author

Eirene Grace P. Valle  
CS 242: Operating Systems  
May 2026

