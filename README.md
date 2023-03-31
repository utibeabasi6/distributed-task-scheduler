# Distributed task scheduler
---
This repository contains the code for a basic distributed task scheduler built in python

## How it works
Multiple instances of the code are run probably in docker containers or kubernetes pods
The code uses Apache zookeeper to implement a basic leader election algorithm and elects a master node. The master node distributes tasks to the workers, which in this case is just adding a random number to a rabbitmq queue. When the master node is stopped, a new master is elected from the remaining workers.
The workers fetch tasks from the queue and execute them, which in this case just involves printing the random numbers out to the console

## How to run
- Start zookeepoer and rabbitmq using the docker-compose file provided with `docker compose up`
- Open a new terminal session and run `python3 app/main.py` to set up the first nstane of the application. Let this run for a few moments to fill up the rabbitmq queue with some random numbers.
- Open two new terminal sessions and repeat. This time, the app starts as a worker and prints out the numbers in the queue
