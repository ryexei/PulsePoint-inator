import random
from pathfinding.mapping import dijkstra

class Patient:
    def __init__(self, id, arrival_time, service_time=None, travel_time=None, path=None):
        self.id = id
        self.arrival_time = arrival_time
        self.travel_time = travel_time
        self.service_time = service_time if service_time is not None else random.randint(1, 15)
        self.path = path

    @staticmethod
    def get_patients(graph, hospital_location):

        patients = []

        # number of patients
        nodes = random.sample([n for n in graph.keys() if n != hospital_location], random.randint(1, 5))

        for node in nodes:
            path, distance = dijkstra(graph, hospital_location, node)

            speed = 160  # km/h
            travel_time = round(distance / speed * 60, 2)
            arrival_time = random.randint(0, 5)

            patients.append(
                Patient(
                    id=str(node),          # or uuid for safety
                    arrival_time=arrival_time,
                    travel_time=travel_time,
                    path=path
                )
            )

        return patients