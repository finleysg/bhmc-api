---
description: Git commit workflow for the BHMC API project
author: Stuart Finley
version: "1.0"
tags: ["git", "commit", "deploy", "quality"]
globs: ["*.*"]
---

This is a manual workflow. Invoke with `/commit-task.md`. The goal is to run quality checks, commit changes with proper documentation, and handle safe deployment.

<detailed_sequence_of_steps>

# Deployment Workflow — Detailed Sequence of Steps

## 1) Identify files in the changeset

Use git to identify files that we need to validate. This only includes files with pending changes:

```xml
<execute_command>
<command>git diff --name-only HEAD</command>
<requires_approval>false</requires_approval>
</execute_command>
```

## 2) Linting Check

Run ruff on any .py file that is in the pending changeset.

```xml
<execute_command>
<command>git diff --name-only HEAD | grep "\.py$" | xargs -r uvx ruff check</command>
<requires_approval>false</requires_approval>
</execute_command>
```

If ruff reports issues, fix them before proceeding. This will naturally stop Cline if the command fails non-zero.

## 3) Test Execution

Run the test suite to ensure code correctness. Stop if tests fail:

```xml
<execute_command>
<command>uv run python manage.py test</command>
<requires_approval>false</requires_approval>
</execute_command>
```

If any test failures, fix them before proceeding.

## 4) Stage Files

If all checks pass, stage all modified files:

```xml
<execute_command>
<command>git add .</command>
<requires_approval>false</requires_approval>
</execute_command>
```

## 5) Generate Commit Message

Prepare a commit message based on git status:

- First, get the git status to understand changes:

```xml
<execute_command>
<command>git status --porcelain</command>
<requires_approval>false</requires_approval>
</execute_command>
```

- Then generate a summary and bullet points for the commit message.

## 6) Create Commit

Execute the commit with the generated message:

```xml
<execute_command>
<command>git commit -m "<generated-message>"</command>
<requires_approval>true</requires_approval>
</execute_command>
```

## 7) Push Prompt

Ask user if they want to push the code:

```xml
<ask_followup_question>
<question>Should I push the code to the repository?</question>
<options>["Yes", "No"]</options>
</ask_followup_question>
```

If "No", conclude workflow.

## 8) Branch Validation

If "Yes", check current branch:

```xml
<execute_command>
<command>git branch --show-current</command>
<requires_approval>false</requires_approval>
</execute_command>
```

If on "main", prompt for new branch:

```xml
<ask_followup_question>
<question>We are on main branch. Please provide a branch name to create:</question>
</ask_followup_question>
```

Then create and switch:

```xml
<execute_command>
<command>git checkout -b <branch-name></command>
<requires_approval>true</requires_approval>
</execute_command>
```

## 9) Push Repository

Push to remote:

```xml
<execute_command>
<command>git push</command>
<requires_approval>true</requires_approval>
</execute_command>
```

## 10) Conclusion

Workflow complete.

</detailed_sequence_of_steps>

<notes>
- Manual workflow; invoke with `/commit-task.md`.
- Stop and fix issues if any step fails.
- Ensure commit policy is respected by having explicit user approval.
- Memory bank updates should be brief but reflective.
</notes>
