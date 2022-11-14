# ARTION manual

## Table of Contents

- **[Introduction](#introduction)**<br>
- **[Installation](#installation)**<br>
- **[Platform documentation](#platform-documentation)**<br>
  + **[Web](#web)**<br>
  + **[Mobile](#mobile)**<br>


## Introduction

This tool was developed by the KIOS Research and Innovation Center of Excellence of the University of Cyprus within 
the framework of the project ARTION. The project ARTION (Disaster Management Artificial Intelligence Knowledge 
Network), January 2021 -June 2022, was funded by the European Union’s Call for proposals in the field of Civil 
Protection under the Union Civil Protection Knowledge Network under grant agreement 101017763. The objectives of the 
project were to bridge the gap between AI scientists and disaster management experts, build capacity and competency 
of first responders in the use of AI technology, share knowledge, data and algorithms, and stimulate further AI 
research towards application-specific challenges faced throughout the disaster management cycle.

Within the framework of the project, datasets were collected during realistic field exercises and algorithms were 
developed for emergency response missions. 
All of them are available at: https://www.kios.ucy.ac.cy/ARTION/disaster-management-ai-portal/

This tool was developed with the contribution of the end-user partners of the project. The Cyprus Civil Defense, 
in Cyprus, contributed with the specification of the requirements and with the organization of several field 
exercises for testing purposes. Moreover, the Directorate-General of Civil Protection for Sardinia Region, in 
Sardinia, Italy, contributed to the final testing of the tool.

&uparrow; [Back to top](#table-of-contents)

## Installation

1. Install [Docker](https://www.docker.com/) and [Docker-Compose](https://docs.docker.com/compose/) on your machine
2. Clone this repository on your machine `git clone https://github.com/KIOS-Research/ARTION.git`
3. Run the command `docker-compose up -d --build` from cmd/terminal 

Once the project starts is accessible at `localhost:9055/`

The containers will auto-restart when docker restart on your machine. In order to stop the ARTION project container, 
you can execute the command `docker-compose down` from cmd/terminal

**Note 1:** In order for the mobile app to be able to connect, your server must have a valid SSL certificate. The URL of the app
should be in the format https://{my-hostname}/ to work properly. Once the setup of the server is done, you should 
change in the `.env.dev` file the **SERVER_URL** variable
 
**Note 2:** You should update **TIME_ZONE** variable based on your local timezone in `.env.dev` file. Default timezone
is set to Europe/Nicosia. The available timezones can be found in
[list of timezones](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)

&uparrow; [Back to top](#table-of-contents)


## Platform documentation

When the application starts it has a superuser created in order to be able to create users 
of the platform. In order to create users navigate to administration site of the project, at
`localhost:9055/admin/` and use the credentials *admin* and *admin1234!*.

### Web

#### Create users

On the left panel select *Users* under *Authentication and authorization*
Click *Add User* in the top right corner
Type username and password of the new user and then click on *Save and continue editing*
In the form complete First name and Last name of the user (it is required in order to identify the user in the list of 
users when sending a chat message)
If the user should access the web platform add the *ccc* group to the chosen groups list otherwise 
if the user is only for mobile application don't include the group.

#### Login

Login to the platform using the credentials of a *ccc* user. The user who creates the mission is considered  as the 
central commander of the mission (the one who will receive the messages from mobile users). More users can sign in 
from web in the same mission but only the one who create the mission is able to receive the chat messages.

#### Predefined team

Predefined teams are created before a mission is started for regular teams that are mostly in missions together. 
Predefined teams give the opportunity for a faster startup of an emergency mission by quickly assign teams in the 
specific mission. 

To view, add, and manage predefined teams, user can select from the menu on the left "Predefined Teams". By clicking 
"New Team" in the top right corner the user can create a new predefined team by adding the team name and users and 
saving the changes. Additionally, by clicking on the name of a predefined team in the list of all predefined teams, 
the details of that team is shown and the user can modify them. By selecting "Delete Team" from the list of all teams
the predefined team is deleted.

#### Car

Cars should be registered in the platform before the starting of a mission. 

To view, add, and manage cars, user can select from the menu on the left "Cars". By clicking 
"New Car" in the top right corner the user can register a new car by adding the licence plates and registration number 
of the vehicle and saving the changes. Additionally, by clicking on the licence plates of a car in the list of all cars, 
the details of that car is shown and the user can modify them. By selecting "Delete Car" from the list of all cars
the car is deleted.

#### Mission

To view, add, and manage missions, user can select from the menu on the left "Missions". By clicking 
"New Mission" in the top right corner the user can start a new mission by adding the name 
of the mission and saving the changes. By clicking "Map" from the list of missions the user can navigate to an active or 
completed mission to see the details and by clicking "Complete" the user determines that the specific mission is completed.

**Mission Code:** When a new mission is created is produced a unique mission code which is used by mobile users in 
order to register to this mission. The mission code can be found in the top bar once the user is inside a mission.

##### Assign predefined team

Once user create a mission, is navigated to the available predefined teams and is able to assign it to the mission. **Note** 
here that are shown only teams that all users are not assigned in a different active mission. By clicking "Assign" the
team is automatically assigned to the mission.

##### Assign a car

The user can assign a vehicle as long as it is not in an active mission. Vehicle assignment can be achieved by 
selecting “Cars” from the menu on the left and then selecting “Assign”. Then, in the window that will appear, 
the user is asked to select the team that wants to assign the specific vehicle. Additionally, the user can release a 
vehicle from the mission by selecting “Release” on list of all cars.

##### Manage teams

Once the user has added all the predefined teams that needed in the mission, can view, edit or add custom teams by 
selecting from the menu on the left "Mission Teams". Then, by clicking on the name of a group, the user can view and 
edit the details of that team. By selecting "Delete Team" the specific team is removed from the mission. By selecting
"New Team" in the top right, the user can assign new custom teams in the mission.

**Note:** The member of a team should be added before the mobile users login in the app. Adding a member in a later 
stage might cause issues with chat functionality

##### Mission map 

The map can be displayed by selecting "Map" on the left side menu. The locations of users who are in a team of the 
mission are automatically shown in the map. Additionally, the user can draw on map points and lines of interest, measure
distances, and chat with other users. Drawing or deleting points of interest can be achieved through the tool located 
to the right side of the map. By clicking on a point or route in the map, the details of the feature is shown with the
ability to send the feature to other users.

##### Chat

The user has the ability to chat with other users by selecting chat icon at the bottom right of the map. 
Next, selects the person that wants to chat with, and start the conversation. The user can receive points and routes of 
interest, images, and text messages from other users. Points and routes of interest and images are geotagged so the user 
can add them to the map by selecting "View on map" in each chat message.

**Note:** Chat features are removed from map when the map is reloaded and the user can add them again from chat history
 
&uparrow; [Back to top](#table-of-contents)


### Mobile

ARTION mobile application is available in both [App Store](https://apps.apple.com/cy/app/artion/id1623161167) 
and [Play Store](https://play.google.com/store/apps/details?id=io.ionic.artion) for downloading.

#### Setup

Once the user downloads and start the application should set the server URL. Once the URL is set the user is able to use
the application.

**Note:** In order for the mobile app to be able to connect, your server must have a valid SSL certificate.

#### Login

User is able to log in the application by completing their credentials taken from the administrator of the platform.

#### Join a mission

After user is successfully logged in the application is able to join an active mission by setting the mission code 
provided by Mission commander once the mission is created.

#### Grant application permissions

The application is using location and camera permission. Once the respective popups appear asking for the permissions 
user should give access to the application in order to work properly.

#### Location

The location of the user is automatically tracked and shown in map by default. The user has the ability to add in map 
the path that followed and the location and paths of his team by selecting the specific layers from the layer menu. 
Location of user is updated once there is a change in location and is shared with team and Mission commander automatically.

#### Map features

User is able to add Point and Routes of interest and photos in the map by opening the features menu and selecting the 
appropriate category. By clicking in a feature of the map, the user can view its details, delete it, or send the 
feature to his team or Mission commander (User who created the mission). 

#### Chat

User can navigate to chat by selecting *Chat* in the bottom menu. User has two predefined chats, one with the Mission
Commander and one with his team. User can receive and send text and map feature messages. Also, the user has the ability
to add in the map features that received from chat.

#### Settings

By navigating to the setting page of the app, user can switch language between English and Greek, exit mission and 
logout the application.

&uparrow; [Back to top](#table-of-contents)
