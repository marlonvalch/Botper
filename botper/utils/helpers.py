
def strikethrough(text):
	# Unicode strikethrough for each character
	return ''.join([c + '\u0336' for c in text])

def format_task_card(tasks, platform="webex"):
	"""
	Returns a card payload for the given platform with CRUD operations.
	For webex/teams: Adaptive Card JSON with Delete and Modify buttons.
	For zoom: Zoom Chatbot Card JSON.
	"""
	if platform in ("webex", "teams"):
		# Create task containers with action buttons
		task_containers = []
		
		for task in tasks:
			task_id = str(task.get('_id', ''))
			checked = task.get('completed', False)
			title = strikethrough(task['title']) if checked else task['title']
			
			# Create a container for each task with title and action buttons
			task_container = {
				"type": "Container",
				"items": [
					{
						"type": "ColumnSet",
						"columns": [
							{
								"type": "Column",
								"width": "stretch",
								"items": [
									{
										"type": "TextBlock",
										"text": title,
										"wrap": True,
										"size": "Medium",
										"color": "Attention" if checked else "Default"
									}
								]
							},
							{
								"type": "Column", 
								"width": "auto",
								"items": [
									{
										"type": "ActionSet",
										"actions": [
											{
												"type": "Action.Submit",
												"title": "✏️",
												"tooltip": "Modify Task",
												"data": {
													"action": "modify",
													"task_id": task_id,
													"task_title": task['title']
												}
											},
											{
												"type": "Action.Submit",
												"title": "🗑️",
												"tooltip": "Delete Task",
												"data": {
													"action": "delete",
													"task_id": task_id
												}
											}
										]
									}
								]
							}
						]
					}
				],
				"separator": True if task_containers else False
			}
			task_containers.append(task_container)
		
		# Build the complete card
		card = {
			"$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
			"type": "AdaptiveCard",
			"version": "1.3",
			"body": [
				{
					"type": "TextBlock", 
					"text": "📋 Your Tasks", 
					"weight": "Bolder", 
					"size": "Large",
					"horizontalAlignment": "Center"
				}
			] + task_containers
		}
		
		# If no tasks, show empty message
		if not tasks:
			card["body"].append({
				"type": "TextBlock",
				"text": "No tasks yet! Use 'task <description>' to create one.",
				"wrap": True,
				"horizontalAlignment": "Center",
				"color": "Attention"
			})
		
		return card
	elif platform == "zoom":
		# Zoom Chatbot Card JSON (simplified)
		items = []
		for task in tasks:
			checked = task.get('completed', False)
			title = strikethrough(task['title']) if checked else task['title']
			items.append({
				"type": "checkbox",
				"text": title,
				"value": str(task.get('_id', '')),
				"checked": checked
			})
		card = {
			"head": {"text": "Tasks"},
			"body": items
		}
		return card
	else:
		return {}
