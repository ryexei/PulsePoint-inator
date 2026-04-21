from pathfinding.mapping import dijkstra


class Ambulance:
    def __init__(self, id, location, positions=None, speed=100):
        self.id = id
        self.patient_id = None
        self.location = location
        self.available = True
        self.available_at = 0
        self.busy_until = 0
        self.current_patient = None
        self.state = "IDLE"  # IDLE, TO_PATIENT, SERVICING, RETURNING
        self.service_timer = 0
        self.target_patient = None
        self.return_path = []
        self.node_states = None
        self.target_node = None
        self.sim_time = None
    

        # visualization attributes
        self.positions = positions
        if positions:
            self.x, self.y = positions[location]
        else:
            self.x, self.y = 0, 0  # Default position if not provided
       


        # movement attributes
        self.path = []
        self.target_index = 0
        self.speed = speed  # pixels per second
        self.moving = False        

    def time(self, total_distance):
        speed = 160  # km/h
        return round(total_distance / speed * 60, 2)

    def dispatch(self, graph, patient_location, hospital_location):

        path_to_patient, dist1 = dijkstra(graph, self.location, patient_location)
        path_to_hospital, dist2 = dijkstra(graph, patient_location, hospital_location)
        
        speed = 160
        travel_time_patient = round(dist1 / speed * 60, 2)  # minutes
        total_distance = dist1 + dist2
        total_time = round(total_distance / speed * 60, 2)

        full_path = path_to_patient + path_to_hospital[1:]

        return {
            "to_patient_path": path_to_patient,
            "to_hospital_path": path_to_hospital,
            "full_path": full_path,
            "travel_time_to_patient": travel_time_patient,
            "total_time": total_time,
            "total_distance": total_distance
        }
    
    def set_path(self, path):
        if path and path[0] == self.location:
            path = path[1:]  # Skip the current location

        self.path = path
        self.target_index = 0
        self.moving = True

    def update(self, dt, sim_time, dispatch_sys):
        patient = dispatch_sys.patient_map.get(str(self.patient_id))

        ###### STATE 1: MOVING ######
        if self.state in ["TO_PATIENT", "RETURNING"]:

            if not self.moving or self.target_index >= len(self.path):
                return

            target_node = self.path[self.target_index]

            if target_node not in self.positions:
                print(f"Warning: No position for node {target_node}")
                self.moving = False
                return

            tx, ty = self.positions[target_node]

            dx = tx - self.x
            dy = ty - self.y
            dist = (dx**2 + dy**2) ** 0.5

            # ---------------- ARRIVAL AT NODE ----------------
            if dist < self.speed * dt:
                self.x, self.y = tx, ty
                self.location = target_node
                self.target_index += 1

                # ---------------- END OF PATH ----------------
                if self.target_index >= len(self.path):
                    self.moving = False
                    self.path = []
                    self.target_index = 0

                    # 🚨 STATE TRANSITIONS ONLY HERE
                    if self.state == "TO_PATIENT":
                        self.state = "SERVICING"
                        self.service_timer = self.service_time

                        self.node_states[str(self.patient_id)] = "SERVICING"

                        dispatch_sys.add_log(
                            sim_time,
                            "ARRIVED",
                            f"Amb {self.id+1} reached P{self.patient_id}",
                            patient
                        )      

                    elif self.state == "RETURNING":
                        self.state = "IDLE"

                        dispatch_sys.add_log(
                            sim_time,
                            "AVAILABLE",
                            f"Amb {self.id+1} ready at hospital"
                        )

            else:
                self.x += (dx / dist) * self.speed * dt
                self.y += (dy / dist) * self.speed * dt

        ###### STATE 2: SERVICING ######
        elif self.state == "SERVICING":

            self.service_timer -= dt

            if self.service_timer <= 0:
                self.node_states[str(self.target_node)] = "DONE"
                
                dispatch_sys.add_log(
                    sim_time,
                    "SERVICE_DONE",
                    f"Amb {self.id+1} finished P{self.patient_id}",
                    patient
                )

                self.state = "RETURNING"
                self.set_path(self.return_path)
                self.target_index = 0
                self.moving = True
                
                dispatch_sys.add_log(
                    sim_time,
                    "RETURNING",
                    f"Amb {self.id+1} heading to hospital"
                )

                