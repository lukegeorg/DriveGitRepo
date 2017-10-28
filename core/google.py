from __future__ import print_function
import httplib2
import os
import cgi

from apiclient import discovery
from apiclient import errors
from apiclient.http import MediaFileUpload
from apiclient.http import MediaIoBaseDownload
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

from core import args
from core import utilities

try:
	import argparse
	args.Arguments.addArguments(tools.argparser)
	flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
	flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/drive-python-quickstart.json
# SCOPES = 'https://www.googleapis.com/auth/drive.metadata.readonly'
SCOPES = 'https://www.googleapis.com/auth/drive.file'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Drive API Python Quickstart'
REPO_FOLDER_NAME = 'Repositories'

F_ID = 'id'
F_NAME = 'name'
F_MIME_TYPE = 'mimeType'
F_TRASHED = 'trashed'
F_PARENT = 'parent'
F_PARENTS = 'parents'
F_FILES = 'files'
F_SIZE = 'size'
F_VERSION = 'version'
F_HEAD_REVISION_ID = 'headRevisionId'
F_REVISIONS = 'revisions'
F_MODIFIED_TIME = 'modifiedTime'

def getMetadataFields():
	return (F_ID, F_MIME_TYPE, F_NAME, F_TRASHED, F_SIZE, F_VERSION, F_HEAD_REVISION_ID)

def getMediaFileUpload(fileToUploadPath):
	return MediaFileUpload(fileToUploadPath, mimetype='application/binary')

def containsRevision(revisions, revisionId):
	for revision in revisions:
		if revision[F_ID] == revisionId:
			return True

	# The head revision hasn't been found
	return False

class GoogleServiceApi:
	"""Google Service Api factory"""

	# CTOR
	def __init__(self):
		self._service = None
		self._repoFolder = None
		print("Google lib created")

	def getCredentials(self):
		"""Gets valid user credentials from storage.

		If nothing has been stored, or if the stored credentials are invalid,
		the OAuth2 flow is completed to obtain the new credentials.

		Returns:
			Credentials, the obtained credential.
		"""
		home_dir = os.path.expanduser('~')
		credential_dir = os.path.join(home_dir, '.credentials')
		if not os.path.exists(credential_dir):
			os.makedirs(credential_dir)
		credential_path = os.path.join(credential_dir, 'repoSync.json')

		print('Looking for stored credentials ...')
		store = Storage(credential_path)
		credentials = store.get()
		if not credentials or credentials.invalid:
			print('Credentials not valid or null. Begin authorization process ...')
			credentials = self.createCredentials(store)
			print('Authentication succeded, storing credentials to ' + credential_path)
		else:
			print('Credentials found')
			if flags.resetCredentials:
				print('Reset existing credentials ...')
				os.remove(credential_path)
				print('Existing credentials removed, begin authentication process ...')
				credentials = self.createCredentials(store)
				print('Authentication succeded, storing credentials to ' + credential_path)

		return credentials

	def createCredentials(self, store):
		flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
		flow.user_agent = APPLICATION_NAME
		if flags:
			return tools.run_flow(flow, store, flags)
		else: # Needed only for compatibility with Python 2.6
			return tools.run_flow(flow, store)

	def getService(self):
		print('Getting Google Api Service ...')

		if self._service is None:
			print('Service not yet initialized. Initializing ...')
			credentials = self.getCredentials()
			http = credentials.authorize(httplib2.Http())
			self._service = discovery.build('drive', 'v3', http=http)
			print('Service initialized')
		return self._service

	def createRepo(self, fileToUploadPath, repoFileName):
		"""Upload a new bundle file on drive. If the file already exists, throw an exception"""

		# Check that the file hans't been previously uploaded
		driveRepo = self.getRepo(repoFileName)

		if driveRepo is None:
			# Get the repo folder
			repoFolder = self.getRepoFolder()

			# Upload the repository
			return self.uploadFile(fileToUploadPath, repoFileName, repoFolder[F_ID])
		else:
			raise Exception("The repository '" + repoFileName + "' already initialized on the google drive. Cannot initialize the repository")

	def updateRepo(self, fileToUploadPath, googleRepoId):
		"""Update a new version of the repository"""

		print('Uploading file "' + fileToUploadPath + '" to google repository id ' + googleRepoId + " ...")

		# Get the repo folder
		repoFolder = self.getRepoFolder()

		# Upload the repository
		fileContent = getMediaFileUpload(fileToUploadPath)

		result = (self
			.getService()
			.files()
			.update(
				fileId=googleRepoId,
				media_body=fileContent,
				fields=utilities.concatenateFields(getMetadataFields()))
			.execute())

		print('Upload complete')

		return result

	def checkFolderExists(self, folderName):
		print("Trying to get folder with name: '" + folderName + "' ...")
		return self.getSingleQueryResult(F_NAME + "='" + folderName + "'", None)

	def createFolder(self, folderName, parentID):
		body = {
			F_NAME: folderName,
			F_MIME_TYPE: 'application/vnd.google-apps.folder'
        }
		if parentID:
			body[F_PARENT] = [{F_ID: parentID}]
		root_folder = self.getService().files().create(body = body).execute()
		return root_folder

	def getRepo(self, repoFileName):
		"""Returns the repository bundle file using the given name"""

		# Retrieve the repository folder
		repoFolder = self.getRepoFolder()

		# Write the query
		query = F_NAME + "='" + repoFileName + "' and '" + repoFolder[F_ID] + "' in " + F_PARENTS

		# Execute the query along with the metadata fields
		return self.getSingleQueryResult(query, getMetadataFields())

	def executeQuery(self, queryString, fields):
		"""Execute the given query in string format"""

		query = cgi.escape(queryString)
		filesProxy = self.getService().files()

		body = {
			'q': query,
		}

		if fields is None:
			return filesProxy.list(**body).execute()
		else:
			fieldsClause = "files(" + utilities.concatenateFields(fields) + ")"
			return filesProxy.list(fields=fieldsClause, **body).execute()

	def getSingleQueryResult(self, queryString, fields):
		queryResult = self.executeQuery(queryString, fields)
		files = queryResult[F_FILES]
		nrResults = len(files)
		print(str(nrResults) + " files found for query '" + queryString + "'")

		if nrResults == 0:
			return None
		elif nrResults == 1:
			return files[0]
		else:
			raise LookupError('Cannot get single result: ' + nrResults + ' files found for query ' + queryString + "'")

	def uploadFile(self, fileToUploadPath, driveName, parentID):
		fileContent = getMediaFileUpload(fileToUploadPath)

		fileBody = {F_NAME: driveName}
		if parentID is not None:
			fileBody[F_PARENTS] = [ parentID ]

		result = (self
			.getService()
			.files()
			.create(
				media_body=fileContent,
				body=fileBody,
				fields=utilities.concatenateFields(getMetadataFields()))
			.execute())

		return result

	def downloadFile(self, destinationFilePath, driveFileId):
		downloadRequest = (self
			.getService()
			.files()
			.get_media(fileId=driveFileId))

		with open(destinationFilePath, 'wb') as file:

			print("Start downloading file " + driveFileId + " ...")
			mediaRequest = MediaIoBaseDownload(file, downloadRequest)

			while True:
				try:
					downloadProgress, done = mediaRequest.next_chunk()
				except errors.HttpError as error:
					print('An error occurred: %s' % error)
					os.remove(destinationFilePath)
					return
				if downloadProgress:
					print('Download Progress: %d%%' % int(downloadProgress.progress() * 100))
				if done:
					print('Download Complete at ' + destinationFilePath)
					return

	def getFileMetaData(self, fileId):
		# Get the file along with metadata fields
		fileResult = (self
			.getService()
			.files()
			.get(
				fileId=fileId,
				fields=utilities.concatenateFields(getMetadataFields()))
			.execute())

	def getRepoFolder(self):
		"""Return an instance of the repository folder object"""

		if self._repoFolder is None:
			folderName = REPO_FOLDER_NAME
			print("Look for repository folder '" + folderName + "' ...")
			self._repoFolder = self.checkFolderExists(folderName)

			if not self._repoFolder:
				print("Folder '" + folderName + "' does not exist on drive. Create it ...")
				self._repoFolder = self.createFolder(folderName, None)
				print("Folder '" + folderName + "' created with ID='" + self._repoFolder[F_ID] + "'")
			else:
				print("Folder '" + folderName + "' retrieved with ID='" + self._repoFolder[F_ID] + "'")
		
		return self._repoFolder

	def deleteAllRevisionButHead(self, fileMetadata):
		"""Delete all revisions of the file except the head revision"""

		fileId = fileMetadata[F_ID]
		fileHeadRevisionId = fileMetadata[F_HEAD_REVISION_ID]

		revisionResponse = (self
			.getService()
			.revisions()
			.list(fileId=fileId)
			.execute())

		revisions = revisionResponse[F_REVISIONS]

		print(str(len(revisions)) + ' revisions found for fileId=' + fileId)

		if not containsRevision(revisions, fileHeadRevisionId):
			raise errors.Error('The head revision "' + fileHeadRevisionId + '" has not been found within the file revisions')

		for revision in revisions:
			# Delete all revisions except the head revision
			revisionId = revision[F_ID]
			if revisionId != fileHeadRevisionId:
				print('Deleting revision with id="' + revision[F_ID] + '". Revision last modified on ' + revision[F_MODIFIED_TIME])

				result = (self
					.getService()
					.revisions()
					.delete(
						fileId=fileId,
						revisionId=revisionId)
					.execute())