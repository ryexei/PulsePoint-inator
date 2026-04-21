from entities.patients import Patient as p
from entities.ambulance import Ambulance as a
from pathfinding.mapping import dijkstra

class Scheduler:
    def __init__(self, patients, ambulances, hospital_location, graph):
        self.patients = patients
        self.ambulances = ambulances
        self.hospital_location = hospital_location 
        self.graph = graph

    def assign_patient(self, patient):
        # Find the first available ambulance
        amb = min(self.ambulances, key=lambda a: a.busy_until)

        # Dispatch time is when ambulance is free or when patient arrives
        dispatch_time = max(amb.busy_until, patient.arrival_time)

        # Compute travel time from ambulance to patient
        path1, dist1 = dijkstra(self.graph, amb.location, str(patient.id))
        path2, dist2 = dijkstra(self.graph, str(patient.id), self.hospital_location)

        speed = 160
        travel_time_to_patient = dist1 / speed * 60
        total_travel_time = (dist1 + dist2) / speed * 60
        

        # Start service after travel
        start_service = dispatch_time + travel_time_to_patient
        completion_time = start_service + patient.service_time

        turnaround_time = completion_time - patient.arrival_time
        waiting_time = dispatch_time - patient.arrival_time + travel_time_to_patient
        
        # Update ambulance state
        amb.busy_until =  dispatch_time + total_travel_time
        amb.location = self.hospital_location

        return {
            "patient_id": patient.id,
            "ambulance_id": amb.id,

            "arrival_time": patient.arrival_time,
            "service_time": patient.service_time,

            "dispatch_time": dispatch_time,
            "travel_time": patient.travel_time,

            "start_service": start_service,
            "completion_time": completion_time,

            "waiting_time": waiting_time,
            "turnaround_time": turnaround_time,

            "response_ratio": None,

            "queue_wait": dispatch_time - patient.arrival_time,
        }


    @staticmethod
    def compute_metrics(results):
        n = len(results)

        total_wait = sum(r["waiting_time"] for r in results)
        total_turn = sum(r["turnaround_time"] for r in results)

        avg_wait = total_wait / n if n else 0
        avg_turn = total_turn / n if n else 0

        total_time = max(r["completion_time"] for r in results) if n else 0

        # NEW METRICS
        max_wait = max(r["waiting_time"] for r in results) if n else 0
        min_wait = min(r["waiting_time"] for r in results) if n else 0

        throughput = n / total_time if total_time > 0 else 0

        return {
            "count": n,
            "avg_wait": avg_wait,
            "avg_turn": avg_turn,
            "total_time": total_time,
            "max_wait": max_wait,
            "min_wait": min_wait,
            "throughput": throughput
        }


    # First-Come-First-Serve Scheduling
    def fcfs(self):
        patients = sorted(self.patients, key=lambda p: p.arrival_time)
        results = []

        for p in patients:
            result = self.assign_patient(p)
            results.append(result)

        return results



    # Shortest Job First Scheduling
    def sjf(self):
        patients = self.patients[:]
        results = []
        current_time = 0
        
        while patients:
            # Filter patients who have arrived by current_time
            available_patients = [p for p in patients if p.arrival_time <= current_time]
            
            if not available_patients:
                # Move time forward if no patient is ready
                current_time = min(p.arrival_time for p in patients)
                continue

            # Pick the patient with the shortest service time
            # If tie, pick the one who arrived first, then by ID
            patient = min(available_patients, key=lambda p: (p.service_time, p.arrival_time, int(p.id)))

            # Assign patient to an ambulance and compute metrics
            result = self.assign_patient(patient)
            results.append(result)

            # Remove patient from the queue
            patients.remove(patient)

        return results

    # evicted !!
    # Longest Job First Scheduling
    # def ljf(self):
    #     patients = self.patients[:]
    #     results = []

    #     while patients:
    #         # Current time is the earliest ambulance availability or first patient arrival
    #         current_time = max(
    #            [p.arrival_time for p in patients] + [a.busy_until for a in self.ambulances]
    #        )

    #         # Filter patients who have arrived by current_time
    #         available_patients = [p for p in patients if p.arrival_time <= current_time]
    #         if not available_patients:
    #             # Move time forward if no patient is ready
    #             current_time = min(p.arrival_time for p in patients)
    #             continue

    #         # Pick the patient with the longest service time
    #         # If tie, pick the one who arrived first, then by ID
    #         patient = max(available_patients, key=lambda p: (p.service_time, -p.arrival_time, -int(p.id)))

    #         # Assign patient to an ambulance and compute metrics
    #         result = self.assign_patient(patient)
    #         results.append(result)

    #         # Remove patient from the queue
    #         patients.remove(patient)

    #     return results
        
    # Highest Response Ratio Next Scheduling
    def hrrn(self):
        patients = self.patients[:]
        results = []
        current_time = 0

        while patients:
            # Filter patients who have arrived by current_time
            available_patients = [p for p in patients if p.arrival_time <= current_time]

            if not available_patients:
                # Move time forward if no patient is ready
                current_time = min(p.arrival_time for p in patients)
                continue

            # Key function: response ratio with tie-breakers
            def hrrn_key(p):
                waiting_time = current_time - p.arrival_time
                rr = (waiting_time + p.service_time) / p.service_time
                # Tie-breakers:
                # - arrival_time ↑ (smaller = higher priority)
                # - patient ID ↑ (smaller = higher priority)
                return (rr, -p.arrival_time, -int(p.id))

            # Pick patient with highest response ratio and tie-breakers
            patient = max(available_patients, key=hrrn_key)

            # Assign patient to an ambulance and compute metrics
            result = self.assign_patient(patient)
            results.append(result)

            # Remove patient from the queue
            current_time = result["dispatch_time"]
            patients.remove(patient)

        return results