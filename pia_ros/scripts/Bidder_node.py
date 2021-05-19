#!/usr/bin/env python3

from Task import Task
from math import sqrt
import copy
import rospy
from pia_ros.srv import ProvideTauc, ProvideTaucResponse, DeclareWinner, DeclareEnd

def agent_to_object():
	# This function creates and returns object of a type Robot by using paramteres
	# available on server under name /agents. Server paramateres are names and attributes 
	# uploaded by pia_ros.launch file from Tasks.yaml file.

	robots = []
	robots = rospy.get_param("/agents")

	index = rospy.get_name().split("Robot")
	location = robots[int(index[1])-1]["location"].split(", ")														# <=== ovo treba pametnije napraviti - M

	return Robot(robots[int(index[1])-1]["name"],robots[int(index[1])-1]["velocity"],location[0],location[1])

class Robot():
	# Object created with a type of this class represents agent and its attributes
	# contained in the Tasks.yaml file. This class provides some useful methods and functions
	# used for Simple Iterated Auction algorithm. It also provides three rosservices of a different
	# type used for node communication.

	def __init__(self, name, velocity, location_X, location_Y):
		# This function initializes object of the class Robot with attributes
		# name, velocity and coordinates X and Y. Furthermore it creates lists Tauc and
		# robot_schedule for each object used for working with objects of type Task.
		# It also creates three rosservice objects of service type ProvideTauc, DeclareWinner and DeclareEnd.

		self.name = name
		self.velocity = velocity
		self.location_X = float(location_X)
		self.location_Y = float(location_Y)
		self.robot_schedule = []
		self.Tauc = []

		try:
			self.s1 = rospy.Service('provide_tauc', ProvideTauc, self.provide_tauc_callback)
			self.s2 = rospy.Service('declare_winner', DeclareWinner, self.declare_winner_callback)
			self.s3 = rospy.Service('declare_end', DeclareEnd, self.declare_end_callback)
		except rospy.ServiceException as exc:
			print("Service already registred, but I am still working!\n")

		rospy.spin()

	def display(self):
		# This functions prints agents name and all its attributes.

		print(f'*{self.name}*')
		print(f'Velocity: {self.velocity} m/s')
		print(f'Location: (x,y) = ({self.location_X},{self.location_Y})\n')

	def provide_tauc_callback(self, req):
		# This function is a callback function for a service type ProvideTauc
		# which is used for providing list that contains all tasks that are on the
		# auction at the given moment. After agent calculates its bid by using ModifiedSSI
		# function, provide_tauc_callback returns object of type ProvideTaucResponse containing
		# object of a type Task, total schedule time and bidders name.

		Tauc = []
		for msg in req.Tauc:
			Tauc.append(Task.to_task(msg))

		self.ModifiedSSI(Tauc)

		self.resp = ProvideTaucResponse()
		self.resp.bid = self.tbid.to_msg()
		self.resp.time = self.b
		self.resp.robot_name = self.name

		return self.resp

	def declare_winner_callback(self, req):
		# This function is a callback function for a service type DeclareWinner
		# which is used for declaring a winner after Bidders have sent their bids.
		# Request is being provided by an Auctioneer.

		if req.win:
			self.robot_schedule = copy.deepcopy(self.bidding_schedule)
			print(f"{self.name}: My bid was ACCEPTED :)")
		else:
			print(f"{self.name}: My bid was NOT accepted :(")

		print(f"{self.name} schedule at this point: ",end='')
		print(f'{self.robot_schedule}\n')

	def declare_end_callback(self, req):
		# This function is a callback function for a service type DeclareEnd
		# which is used for telling Bidders that all tasks have been assigned.
		# Request is being provided by an Auctioneer.

		if req.end:
			print(f'{self.name} final schedule is: {self.robot_schedule}')
			print(f'Total schedule time: {self.b} seconds\n')
			#quit()

	def ModifiedSSI(self, Tauc):
		# This function chooses the task that is going to be bidded from all of the
		# tasks that are on the auction at the given moment. It calculates the best possible
		# position in the current robots schedule by taking into account the shortes time needed
		# for a robot to finish its schedule and other parameteres such as robots type, task cost etc.

		self.b = float('inf')
		self.bidding_schedule = []
		self.bidding_schedule = 0
		self.tbid = 0

		for t in Tauc:
			tmin = 0
			the_best_possible_schedule = []
			for i in range(len(self.robot_schedule) + 1):
				temp_schedule = copy.deepcopy(self.robot_schedule)
				temp_schedule.insert(i, t)
				total_schedule_time = 0
				total_schedule_time = self.get_Schedule_Time(temp_schedule)
				if total_schedule_time < tmin or tmin == 0:
					tmin = total_schedule_time
					the_best_possible_schedule = temp_schedule
				else:
					continue
			if tmin < self.b:
				self.b = tmin
				self.bidding_schedule = the_best_possible_schedule
				self.tbid = t
			else:
				continue

	def get_Schedule_Time(self, schedule):																# <=== uciniti da radi i za negativni dio koordinatnog sustava
		# This function calculates total time needed for a certain robot to finish its schedule.
		# It takes current robots schedule as an argument. First it adds all durations times for
		# every task in the schedule. Then it calculates the shortest possible distance between
		# every two tasks in the schedule and the shortest possible distance between first task and
		# robots start location. After it calculated distance it divides it with the robots velocity
		# to get the time. The function adds that time with all duration times and returns the result.

		total_time = 0

		for t in schedule:
			total_time = total_time + float(t.duration)

		for i in range(len(schedule)):
			if i == 0:
				distance = sqrt(pow((float(schedule[i].location_X) - float(self.location_X)),2) + pow((float(schedule[i].location_Y) - float(self.location_Y)),2))
			else:
				distance = sqrt((float(schedule[i].location_X) - float(schedule[i-1].location_X))**2 + (float(schedule[i].location_Y) - float(schedule[i-1].location_Y))**2)

			total_time = total_time + distance/float(self.velocity)

		return total_time

if __name__ == "__main__":
	# This is 'main function' used for initializing node and creating
	# object of a type Robot.

	rospy.init_node("Robot", anonymous = True)

	try:
		R = agent_to_object()

	except rospy.ROSInterruptException: pass

##			=============================
##			*** ModifiedSSI algorithm ***
##			=============================
##	Input: Set of tasks Tauct, earliest start times PC
##	Output: Vector of finishing times F
##	while |Tauct| > 0 do
##		b = ∞
##		tbid = ∅
##		for all t ∈ Tauct do
##			for all positions p in current schedule S do
##				Insert t in S at p to get S'
##				if isValid(S') and bid(S') < b then
##					b = bid(S'), tbid = t
##				end if
##			end for
##		end for
##		sendBid(b, tbid)
##		rwin, twin = receiveWinner()
##		if r = r win then
##			Insert t win in S at best valid position
##		end if
##		Tauct = Tauct \ twin
##	TightenSchedule(F)
##	return F