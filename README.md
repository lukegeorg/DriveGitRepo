# Drive Git Repo

## Share your git repository on google drive

Store your git repository on google drive using the bundle functionality of git. The scripts push and pull automatically your changes from and to the remote git bundle file starting from a local git repository folder.

The scripts use the google drive api (<https://developers.google.com/api-client-library/python/>) and need a git client installed on the local machine.

---

## repoInit

Initialize the repository on google drive. Usage:

```
$ repoInit.py -g PATH_TO_GIT_REPOSITORY
```

## repoPush

Pushes local commits to the remote repository on google drive. Usage:

```
$ repoPush.py -g PATH_TO_GIT_REPOSITORY
```

Requires the repository initialized on google drive.

## repoSync

Sync (or Clone if the local repository does not exist) the remote repository with the local git repository. Usage:

```
$ repoSync.py -g PATH_TO_GIT_REPOSITORY
```

Requires the repository initialized on google drive.