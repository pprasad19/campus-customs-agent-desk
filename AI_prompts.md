# AI Prompts

Log of prompts given for Homework 5.

## Problem 1 - Vibe coder prompts

### Initial Prompts

Now we are ready to start the assignment. Create an AI_prompts.md file. This file will have a log of the prompts that I will be giving you. Create headings from Problems 1-11 in this file. Then create subheadings titled Initial Prompts and Follow-up Prompt for each of these problems.

### Follow-up Prompt

None was needed.

## Problem 2 - Study the Campus Customs database

### Initial Prompts

Now we will be going to Problem 2. data/campus_customs.db should be opened. Every table and its fields should be looked through thoroughly. The original file should be copied to data/campus_customs_new.db. That working copy will be updated by future problems. The 3 open tickets should be studied so that you know how they are linked to the other tables. The output/harness.md file should be started. For each table, the fields should be listed and one short line regarding the importance of the table for the agents should be written. In future problems, this harness file will keep growing.

### Follow-up Prompt

None was needed.

## Problem 3 - Build the MCP server

### Initial Prompts

Now we will be going to Problem 3. An MCP server in mcp_server/ should be written using FastMCP. It should talk to data/campus_customs_new.db. This does not need to be run or connected in this problem. The tools in this MCP server will be used by every agent in this homework. For now, 3 tools that you know will be needed for the tickets in the database should be written. No need to write more than 3 tools for now. The names of these tools should be clear. Only use the information within the database; no data should ever be invented. In the output/harness.md file, each of the 3 MCP tools should be listed. For every tools, you should include 1) what table it reads, 2) what ticket it helps unlock (101, 102, or 103), 3) 1 sentence explaining why that tool is the most appropriate one for that ticket. Also, a short mcp_server/README.md file should be written. This file should explain what the MCP server is for, what database file it uses, and the 3 tools that it has

### Follow-up Prompt

I also forgot to tell you that do not write vague lines like "reads inventory" in the output/harness.md file. Such responses will be scored low by my graders. The tools should be tied to the ticket.

## Problem 4 - Add the MCP server to vibe coder and test each tool

### Initial Prompts

Now we will be going to Problem 4. First, add the MCP server to this project so that you can call on the necessary tools. The connection JSON text should be saved in .mcp.json should be saved as the project root. Then, test each of the 3 MCP tools. The evidence should be saved in output/mcp_smoke.json. For every tool, make sure to include the prompt you asked the vibe coder, the tool name, and the tool output (this should match the values in data/campus_customs_new.db)

### Follow-up Prompt

None was needed.

## Problem 5 - Build the agent team and grow the MCP tools

### Initial Prompts

Now we will be going to Problem 5. The agentic team for Campus Customs should now be built using Pydantic AI: Boss, Inventory, Accounting, Facilities, and Customer Service. The prompts, models, and agent loops should all be included so that they can delegate work to each other with full connectivity. The agent prompts should be put in backend/prompts/ - only one file per agent. The data types should be put in backend/models.py. The agent files should be put under backend/ (the layout can vary as long as the 5 roles are clear). For every agent, utilize PORTKEY_API_KEY and only gpt-6-luna. Each prompt should be written in your own words with the shop rules that the agent needs. In comparison to a short generic prompt, I will be given a higher score for more detailed prompts that cover all aspects of an agent's work. Any tools that the agents needs should be added to the MCP server so that they can work on the open tickets. The shop facts should come from the MCP server over data/campus_customs_new.db. A second shop-tools layer that bypasses the MCP should not be invented. The agents should be wired so that they append to output/audit_trail.json as they run - for each agent-loop step, enough should be recorded so that it can be audited later.  Always append to this file, it should not be wiped for each run. In the output/harness.md file, each agent and each MCP tool (including the ones you add in this problem) should be be listed along with which table the tool uses. Add a short safety section as well. This safety section should have the guardrails a real business world would want when agents touch real money and real customers; also put limits that keep the token use in check. The mcp_server/README.md file should be updated so that the tool list matches what you have now.

### Follow-up Prompt

None was needed.

## Problem 6 - Plan the three tickets

### Initial Prompts

Now we will be going to Problem 6. Before the backend is wired, write down what you expect the team to do on each open ticket. output/desk_tickets.html should be built - this should be a page that you can double-click with one tab per ticket (101, 102, and 103). For later problems, add empty Cash and Reflection tabs (for now, these should be left blank or with a short "coming later" note). On each ticket tab, only the expected section should be filled (room for the actual section should be left; you will be filling this after you run the agents later). For each ticket's expected section, write in your own words 1) who the boss should call first and why, 2) all the agent delegations you expect (not "boss calls everyone"), and 3) which MCP tools you expect that run to use. Plans that send every specialist on every ticket score low. You will be comparing this plan to what actually happens when the agents resolve the 3 tickets.

### Follow-up Prompt

None was needed.

## Problem 7 - Backend routes

### Initial Prompts

Now we will be going to Problem 7. The React frontend dashboard (the next problem) will need a backend that it can call. In the backend/main.py file, FastAPI should be used and routes that do the following should be added: 1) Return the 3 tickets and whether each is open or resolved, 2) Take a ticket id and run the agent team on that ticket, 3) return recent agent events (what each agent said and the tools that they used) so that the board can be refreshed, 4) approve a payment or purchase after a human clicks approve (agents only prepare the pay; this route is what will actually change cash), 5) return the current checking balance from cash_accounts, and 6) reset the database to the original values when you want to try a fresh run. The server should be started from the backend/folder with uvicorn main:app --reload --port 8000. This should turn on the backend at http://localhost:8000 so that the frontend dashboard can call those routes. Each route should be listed in one line (what URL/what it does) in the output/harness.md file.

### Follow-up Prompt

Nothing should be pointing to Homework 4. I will be submitting all my Homework 5 files separately. Make sure that this is the case for all the outputs you have created for me on this assignment.

*Importance:* the project was quietly relying on files outside the Homework 5 folder, so it would not have run at all once handed in on its own.

## Problem 8 - Agent dashboard

### Initial Prompts

Now we will be going to Problem 8. The frontend dashboard should be built in frontend/ with React + Vite + TypeScript. The page should call the routes that were built in Problem 7. It should include all the following at the minimum 1) All 3 tickets should be listed, 2) Let you pick one ticket and start the agent team on it, 3) Show each agent and what they are doing/saying while the ticket runs, 4) Mark a ticket as resolved when the run finishes, 5) Show a short summary of what each agent did on that ticket, 6) Let a human approve a purchase or pay when asked, 7) The checking balance should be shown (it should drop after an approved pay). The dashboard should look good. The feel and layout of the site should be very nice; be creative with it since this is a real desk that people would want to sit at. Make it as beautiful and eye-catching as you can. The frontend should be talking to the backend at http://localhost:8000. On the backend, allow the Vite page origin (usually http://localhost:5173) so that the browser has permission to call those routes. npm run dev should open the React desk in the browser so that I can pick the agents and watch agents. In the output/design.md file, write what you chose for the dashboard look (layout, how resolved cash and resolved tickets show up, how agents read differently) and why.  This should include the creative choices that make it feel extra special and make it something that humans would really enjoy utilizing.

### Follow-up Prompt

*Listed below are only the 3 follow-up prompts that led to the most significant changes. Many more follow-up prompts were given throughout this problem to make the site as user-friendly as possible.*

1. "the website looks very ugly right now. put some nice relevant images and icons to make it more visually appealing. maybe also change the color scheme of the site to not make it so boring"

*Importance:* the page looked like a plain data table, and this turned it into something that actually feels like a shop desk you would want to sit at.

2. "why am I not able to sign off on anything for 103"

*Importance:* the shop could only ever ask me to approve payments, so the one ticket that was purely a pricing decision gave me nothing to say yes or no to.

3. "why are none of my tickets saying it is resolved when the run finished"

*Importance:* paying a bill moved the money but never updated the ticket, so work I had already paid for still showed as waiting on me.

## Problem 9 - Resolve the tickets

### Initial Prompts

Now we will be going to Problem 9. Reset the working database data/campus_customs_new.db again before testing the agents on a full run over the 3 tickets so that you can start clean. Make sure to note the starting checking balance. Afterwards, run all 3 tickets on the board (101, 102, 103) until each is resolved. From Problem 6, open output/desk_tickets.html. Within each ticket tab, the Actual section from this run should be filled: what agents worked, what did they delegate, and what tools did they use. The Expected section should be kept so that you can compare the two. Within the Cash tab of the same output/desk_tickets.html file, the money should be itemized. The starting checking balance (after the reset) should be shown. For each ticket, how cash changed when that ticket resolved and why (which purchase/pay, dollar amount) should also be shown. The ending checking balance should match cash_accounts in the working database. Even if the board shows every ticket as resolved, I will lose points for wrong cash math, so make sure that this is correct. In output/resolved_tickets.json, the id, final status, short outcome, the contribution of each agent, and any human approvals should all be saved for each ticket. In output/resolved_board.html, a page that can be double-clicked with a screenshot of the React board for each resolved ticket (101, 102, and 103) should be saved. To output/audit_trail.json, append real runs. Output/harness.md file should be finished so that it covers the tables, 5 agents, MCP tools, API routes, safety rules, and the dashboard.

### Follow-up Prompt

*Listed below are only the 3 follow-up prompts that led to the most significant changes. Many more follow-up prompts were given throughout this problem to make the site as user-friendly as possible.*

1. "Going to use 103 as an example here. If Boss is working and calling Inventory, Inventory should also show it is working. Fix this for 103 and make appropriate changes for the other 2 tickets as well."

*Importance:* the screen only showed an agent's work after it had finished, so for the first 20 seconds of every run the page looked like nothing was happening at all.

2. "I just rejected 102 but the ticket does not say rejected. Fix that. Also, the name of the person signing should be reset everytime I go to a new ticket."

*Importance:* turning a payment down left the ticket saying it was still waiting on me, so a decision I had already made would never go away.

3. "I should not be able to see what to sign/approve until the run is finished, fix that."

*Importance:* the payment slip showed up before the team had finished thinking, so I could have signed off money while the Boss was still deciding whether it was the right call.

## Problem 10 - Reflection

### Initial Prompts

Now we will be moving to Problem 10. In this exercise, output/desk_ticket.html will be opened and the Reflections tab will be filled. Input the following questions in the tab:

1. How would you evaluate the performance of the agents on each ticket and why?
2. For each ticket, how did the Actual compare to the Expected plan you wrote earlier?
3. What would have been simpler with one agent with tools - and why?
4. Describe 3 new problems Campus Customs might face that this agent team could solve with the tools you built.
5. Describe 3 new problems Campus Customs might face that this agent team could not solve with the tools you built, and explain the tools and agents you would need to solve them

### Follow-up Prompt

None was needed.

## Problem 11 - Submit to GitHub

### Initial Prompts

Now we will be moving to Problem 11. The code now needs to be pushed to a public GitHub repository so that my graders can clone it. The repo URL is what I will need to be submitting. The repo URL should also be put in output/github_url.txt. Please keep in mind that the real .env file should not be pushed to the GitHub repo. Both database files should be included under data/ (the original and working copy) so that my graders can run the app easily. Now I will be telling you the expected file layout: AI_prompts.md, requirements.txt, .env.example, .gitignore, .mcp.json, README.md, data/campus_customs.db, data/campus_customs_new.db, mcp_server/server.py, mcp_server/README.md, frontend/, backend/main.py, backend/models.py, backend/prompts/boss.md, backend/prompts/inventory.md, backend/prompts/accounting.md, backend/prompts/facilities.md, backend/prompts/customer_service.md, output/harness.md, output/mcp_smoke.json, output/desk_tickets.html, output/design.md, output/resolved_tickets.json, output/resolved_board.html, output/audit_trail.json, and output/github_url.txt.

The README should explain all of the following: copy original DB to the working copy when you need a clean run, start FastAPI backend, start MCP server, start the React board, and reset the DB before a full 3-ticket run.

### Follow-up Prompt

None was needed.
