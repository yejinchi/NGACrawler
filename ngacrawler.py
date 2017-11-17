import json
import string
import time
import downloader
import mongo_cache
import threading
import multiprocessing
import urllib2, os

SLEEP_TIME = 1
CRAWL_COUNT = 1000
MAX_PROCESS_COUNT = 10
SIGN_INFO_FILE = 'signinfo2.txt'
AVATAR_FILE = 'avatar.txt'
LOG_FILE = 'log.txt'

headers={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:50.0) Gecko/20100101 Firefox/50.0'}

def f_ngacrawler(uid):
	uid = uid + 770000
	print 'f_ngacrawler',uid
	template_url = 'http://bbs.ngacn.cc/nuke.php?__lib=ucp&__act=get&lite=js&uid={}'
	download = downloader.Downloader(mongo_cache.MongoCache())
	signinfo=[]
	
	fw = open(SIGN_INFO_FILE, 'a')
	favatar = open(AVATAR_FILE, 'a')
	start_index = 1
	while start_index <= CRAWL_COUNT:
		#3655762
		#uid=3655762
		uid+=1
		start_index += 1
		while True:
			html = download(template_url.format(uid))
			#find username
			username=get_useruid(html)
			if not username:
				break
				
			#find avatar
			avatar_str = get_avatar_str(html)
			if avatar_str:
				avatar_array = parse_avatar_str(avatar_str)
				for avatar_link in avatar_array:
					download_avatar_img(avatar_link, username)
			
			#find signature
			sign_str=get_sign_str(html)
			if sign_str:
				signinfo.append(username + ':' + sign_str)
			else:
				break
				
			if f_sign_have_image_src(sign_str):
				img_urls = parse_imgsrc(sign_str)
				for img_url in img_urls:
					if img_url:
						favatar.write(img_url + '\n')
						download_sign_img(img_url, username)

			#time.sleep(0.1)
			try:
				ajax = json.loads(html)
			except ValueError as e:
				#print e
				ajax = None
				break
			else:
				print 'username:',ajax['username']
				break
			if len(signinfo) == CRAWL_COUNT:
				fw.write('\n'.join(signinfo))
				fw.write('\n')
				signinfo=[]
	fw.write('\n'.join(signinfo))
	fw.write('\n')
	fw.close()
	favatar.close()
	
def parse_imgsrc(sign_str):
	imgmatch=re.compile(r'(http://[^,"]*?\.png|http://[^,"]*?\.gif|http://[^,"]*?\.bmp|http://[^,"]*?\.jpg)', re.IGNORECASE)
	imgurls=imgmatch.findall(sign_str)
	return imgurls

def download_sign_img(img_url, username):
	global f_log
	global headers
	f_log.write('sign img url:' + img_url + '\n')
	try:
		img_file = urllib2.Request(url=img_url,headers=headers)
		binary_data = urllib2.urlopen(img_file).read()
	except:
		#print 'download sign error',img_url
		f_log.write('except in download sign img, url:' + img_url + '\n')
		return
	img_file_name = ''
	img_file_index = 0
	while True:
		index = img_url.find('/',img_file_index + 1)
		if not index == -1:
			img_file_index = index
		else:
			break
	img_file_name = img_url[img_file_index + 1:]
	if not valid_pic(img_file_name):
		f_log.write('sign img url not pic:' + img_url + '\n')
		return
	if img_file_name:
		f_log.write('download sign pic success:' + username + '-' + img_file_name + '\n')
		img_file_name = './signpic/' + username + '-' + img_file_name
		temp_file = open(img_file_name, 'w')
		temp_file.write(binary_data)
		temp_file.close()
		
def download_avatar_img(img_url, username):
	global f_log
	global headers
	f_log.write('avatar img url:' + img_url + '\n')
	try:
		img_file = urllib2.Request(url=img_url,headers=headers)
		binary_data = urllib2.urlopen(img_file).read()
	except:
		#print 'download avatar error',img_url
		f_log.write('except in download avatar img, url:' + img_url + '\n')
		return
	img_file_name = ''
	img_file_index = 0
	while True:
		index = img_url.find('/',img_file_index + 1)
		if not index == -1:
			img_file_index = index
		else:
			break
	img_file_name = img_url[img_file_index + 1:]
	if not valid_pic(img_file_name):
		f_log.write('avatar img url not pic:' + img_url + '\n')
		return
	if img_file_name:
		f_log.write('download avatar pic success:' + username + '-' + img_file_name + '\n')
		img_file_name = './avatarpic/' + username + '-' + img_file_name
		temp_file = open(img_file_name, 'w')
		temp_file.write(binary_data)
		temp_file.close()

def f_sign_have_image_src(sign_str):
	src_index = sign_str.find('src=\'')
	if src_index == -1:
		return False
	else:
		return True

def get_useruid(html):
	username_beginindex=html.find('uid')
	if username_beginindex == -1:
		return None
	username_endindex=html.find(',', username_beginindex)
	username=html[username_beginindex:username_endindex]
	username=username[username.index(':')+1:len(username)]
	return username

def get_sign_str(html):
	beginindex=html.find('sign":')
	if beginindex==-1:
		return None
	endindex=html.find(',', beginindex)
	sign_str=html[beginindex:endindex]
	sign_str=sign_str[sign_str.index(':')+2:len(sign_str)-1]
	return sign_str
	
def get_avatar_str(html):
	avatar_beginindex = html.find('avatar')
	if avatar_beginindex == -1:
		return None
	avatar_endindex = html.find(',"sign"', avatar_beginindex)
	if avatar_endindex == -1:
		return None
	avatar_str = html[avatar_beginindex:avatar_endindex]
	avatar_str = avatar_str[len('\"avatar\":'):len(avatar_str) - 1]
	avatar_str = avatar_str.replace('\\','')
	avatar_str = avatar_str.replace(' ','')
	avatar_str = avatar_str.replace('{','')
	avatar_str = avatar_str.replace('}','')
	return avatar_str
	
def parse_avatar_str(avatar_str):
	avatar_array = []
	if not avatar_str.find(',') == -1:
		avatar_str = avatar_str[1:len(avatar_str)-1]
		avatar_temparr = avatar_str.split(',')
		for i in avatar_temparr:
			avatar_link = get_avatar_link(i)
			if avatar_link:
				avatar_array.append(get_avatar_link(i))
		return avatar_array
	else:
		avatar_array.append(avatar_str)
		return avatar_array
		
def get_avatar_link(i):
	avatar_beginindex = i.find('\":')
	if avatar_beginindex == -1:
		return None
	if not i.find(':"') == -1:
		avatar_link = i[avatar_beginindex+3:len(i)-1]
		if valid_link(avatar_link):
			#print 'if avatar_link:',avatar_link
			return avatar_link
		else:
			if avatar_link.find('http:') == -1:
				return None
			else:
				avatar_link = avatar_link[avatar_link.find('http:'):]
				#print 'else else avatar_link:',avatar_link
				return avatar_link if valid_link(avatar_link) else None
	else:
		avatar_link = i[avatar_beginindex+2:]
		return avatar_link if valid_link(avatar_link) else None
		#print 'else avatar_link:', avatar_link
	if avatar_link:
		return avatar_link
	else:
		return None
		
def valid_link(url):
	if url[0:5] == 'http:':
		return True
	else:
		return False

def valid_pic(img_file_name):
	file_type = os.path.splitext(img_file_name)
	ftype = file_type[1]
	if ftype == '.jpg' or ftype == '.gif' or ftype == '.png' or ftype == '.JPG' or ftype == '.GIF' or ftype == '.PNG':
		return True
	else:
		return False
		
def thread_call():
	max_threads = 5
	threads = []
	thread_index = 0
	while len(threads) < max_threads:
		print 'while len(threads) < max_threads:'
		thread = threading.Thread(target=f_ngacrawler, args=(thread_index * CRAWL_COUNT,))
		thread_index += 1
		#thread.setDaemon(True)
		thread.start()
		thread.join()
		threads.append(thread)
		
def process_crawler(args, **kwargs):
	#num_cpus = multiprocessing.cpu_count()
	#print 'Starting {} processes'.format(num_cpus)
	processes = []
	for i in range(MAX_PROCESS_COUNT):
		p = multiprocessing.Process(target=f_ngacrawler, args=(i * CRAWL_COUNT,), kwargs=kwargs)
		p.start()
		processes.append(p)
	for p in processes:
		p.join()
	
if __name__ == '__main__':
	f_log = open(LOG_FILE, 'a')
	process_crawler(5)
	f_log.close()