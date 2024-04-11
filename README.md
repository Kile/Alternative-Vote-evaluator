# Alternative Vote evaluator
 This code can get election results from a google form that follows an "alternative vote" system

## Google setup
### Google Form
Below is how an election question should be set up:
<img width="901" alt="image" src="https://github.com/Kile/Alternative-Vote-evaluator/assets/69253692/364b03a2-3b7d-4e3b-82f6-55c4d8611ac1">

Please make sure you set it up such that:
* It is limited to one response per collumn
* The question/title/name of this element is only the name of the role, nothing more
* An additional option named "RON" is included. This stands for a not electing someone and repeating the vote for this position with new candidates. You may choose to not name it RON but that will require some code changes.
* Row names must be a single integer corresponding to the row

### Google Sheet
And that's it in terms of Google Form setup! All you need to count the results it a Google Sheet generated from the results. 
<img width="437" alt="image" src="https://github.com/Kile/Alternative-Vote-evaluator/assets/69253692/68b64c1c-cc04-47cb-b480-87a26e419183">
Click on the "Share" button on that sheet and copy the link. Make sure it is accessible to everyone, and not just your organisation. This link will be used later.


## Code setup
The code requires you to add a file called `first_choices.txt`. This is to determine which role someone is elected for, should they win two roles. Format it as follows:
```txt
<Name>: <Role Name>
<Name>: <Role Name>
...
```
The role name and person name **must** be the same as on the Google form. 

If one role should have more than 1 person elected for it, an additional file named `extra_roles.txt` must be created. This file is OPTIONAL. Format it as follows:
```txt
<Role Name>: <Number of people to elect>
<Role Name>: <Number of people to elect>
...
```
Roles who only need one person elected for them do not need to be included in this file. The role name must be the same as on the Google form.

Then also make sure you have installed all dependencies with `pip3 install -r requirements.txt`


## Running the code
All that is left to do now is running the code! Run it with `python3 main.py`, then paste the spreadsheet link when promted. If you set up the form correctly, the code should now print the winners for each role. If you would like to know more details, such as in what round they were elected and with what percentage and if anyone won a role twice before the code adjusted the result, each action the code did will be logged in `process.log`.
