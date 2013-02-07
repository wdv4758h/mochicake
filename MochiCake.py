# -*- coding: utf-8 -*-
import sys
import re
import bsdconv
import telnetlib
import time
import pyte
import os

CONST = {}
fishList = []
lastCmd = ''
state = 'WAIT_COMMAND'
lastResponce = ''
position = ''

def loadConf ():
    print '載入設定檔...'
    global CONST
    try:
        unknown = ''
        lineTemp = ''
        with open('MochiCake.conf') as conf:
            for line in conf:
                if line[0] == '#':
                    continue
                lineTemp = line
                key, value = line.split(':')
                key = key.lower()
                value = value.strip()
                if value == '':
                    return 'ConfSyntaxError', lineTemp
                elif key in ['user', 'passwd', 'master', 'board']:
                    CONST[key.upper()] = value
                else:
                    CONST[key] = value
                    unknown += line
            if unknown == '':
                return 'Normal', ''
            else:
                return 'UnknownOption', unknown
    except IOError:
        return 'ConfFileNotExist', 'MochiCake.conf'
    except ValueError as e:
        return 'ConfSyntaxError', lineTemp

def genExampleConfFile ():
    print '設定檔不存在, 產生範例設定檔...(MochiCake.conf)'
    with open('MochiCake.conf', 'w') as conf:
        conf.write('#user:\n')
        conf.write('#passwd:\n')
        conf.write('#master:\n')
        conf.write('#board:\n')
        conf.close()
    print '完成, 請先完成設定檔'

def checkLackArgument ():
    lack = []
    for i in ['USER', 'PASSWD', 'MASTER', 'BOARD']:
        if not i in CONST:
            lack.append(i)
    return lack

def checkConf (errState, errMsg):
    print '檢查設定檔語法...'
    if errState == 'Normal':
        pass
    elif errState == 'UnknownOption':
        print '未知的選項 :'
        print errMsg
    elif errState == 'ConfFileNotExist':
        genExampleConfFile()
        exit()
    elif errState == 'ConfSyntaxError':
        print '設定檔語法錯誤 :'
        print errMsg
    lack = checkLackArgument()
    if lack != []:
        print '設定檔中缺少必要選項 :'
        for i in lack:
            print i
        exit()
    print '設定檔載入成功'

def prepareConf ():
    errState, errMsg = loadConf()
    checkConf(errState, errMsg)

def term_comm (w=None, wait=None):
	""" 寫入連線、將回傳內容放進虛擬終端機緩衝區、取得目前虛擬終端機的畫面 """
	if w != None:
		conn.write(w.decode('utf8').encode('big5'))
		if wait:
			s = conn.read_some()
			s = conv.conv_chunk(s)
			stream.feed(s.decode("utf-8"))
	if wait!=False:
		time.sleep(0.1)
		s = conn.read_very_eager()
		s = conv.conv_chunk(s)
		stream.feed(s.decode("utf-8"))
	ret="\n".join(screen.display).encode("utf-8")

	#''' 顯示目前畫面 '''
	#sys.stdout.write("\x1b[2J\x1b[H") #清空畫面，將游標移至左上角
	#sys.stdout.write(ret)
	time.sleep(1)
	return ret

def login(user, passwd):
    print '登入中...'
    s = term_comm().split('\n')
    while True:
        s = term_comm()
        if s.find('[您的帳號]') != -1:
            term_comm('%s\r' % user, wait=True)
            break
    while True:
        s = term_comm()
        if s.find('[您的密碼]') != -1:
            term_comm('%s\r' % passwd, wait=True)
            break
    '''跳過進板公佈欄'''
    term_comm('    ', wait=True)
    print '完成'

def enterBoard (board):
    print '離開使用者名單'
    term_comm('\x1b\x5b\x44', wait=True)

    print '進入看板 %s' % board
    term_comm('\x73%s\n' % board)

    print '完成'
    loadFishList(board)

    print '打開使用者名單...'
    term_comm('\x15', wait=True)
    print '完成'

def loadFishList (board):
    global fishList
    print '載入記錄 (fishes/%s)...' % board

    if not os.path.exists('fishes'):
        os.mkdir('fishes')
    if not os.path.isdir('fishes'):
        os.rename('fishes', 'fishes.tmp')

    open('fishes/'+board, 'a').close()
    fishList = []
    with open('fishes/'+board, 'r') as fishes:
        fishList = [i.strip() for i in fishes]
    for i in fishList:
        print i
    print '完成'

def checkNewFish (lines):
    global fishList
    for line in lines[3:]:
        fishID = line[8:20].strip()
        if fishID == CONST['USER']:
            break
        elif not fishID in fishList:
            '''Got a new fish!'''
            print '發現新魚 : \033[1;31m'+fishID+'\033[m'
            fishList.append(fishID)
            fishes = open('fishes/'+position, 'a')
            fishes.write(fishID+'\n')
            fishes.close()

def responce (s):
    global lastResponce
    if lastResponce != s:
        print '更改故鄉為'+s
        term_comm('\x06\x03'+s+'\n', wait=True)
        print '完成'
        lastResponce = s

def onReceiveCommand (cmd):
    global state
    if state == 'WAIT_COMMAND':
        if cmd in ['[logout]', '[reload]']:
            responce('[收到~ 再次確認~]')
            state = 'WAIT_CONFIRM'
        elif cmd == '[hello]':
            responce('[哈囉>ω<]')
    elif state == 'WAIT_CONFIRM':
        if cmd == '[ok]':
            if lastCmd == '[logout]':
                logout()
            elif lastCmd == '[reload]':
                enterBoard(position)
            state = 'WAIT_COMMAND'
        elif cmd == '[no]':
            responce('[動作取消~]')
            state = 'WAIT_COMMAND'
        else:
            pass

def checkCommand (user, master, lines):
    global lastCmd
    for line in lines[3:]:
        fishID = line[8:20].strip()
        if fishID == master:
            words = line.split()
            if words[-2].startswith('[') and words[-2].endswith(']'):
                cmd = ' '.join(words[-2].split(':'))
                if lastCmd != cmd:
                    print '接收到指令 '+cmd
                    onReceiveCommand(cmd)
                    lastCmd = cmd
            else:
                responce('[看魚~]')
            break;

def logout ():
    responce('[登出中~]')
    print '登出中...'
    '''左左左左左'''
    term_comm('\x1b\x5b\x44')
    term_comm('\x1b\x5b\x44')
    term_comm('\x1b\x5b\x44')
    term_comm('\x1b\x5b\x44')
    term_comm('\x1b\x5b\x44')
    term_comm('\x1b\x5b\x44')

    print '已回到主選單'

    '''登出'''
    try:
        term_comm('g\ng\nq\n')
    except EOFError:
        pass
    exit()

if __name__ == '__main__' or True:
    prepareConf()

    #big5(含uao)，去雙色字，轉utf-8
    conv=bsdconv.Bsdconv("ansi-control,byte:big5-defrag:byte,ansi-control|skip,big5:utf-8,bsdconv_raw")
    conv.init()
    stream = pyte.Stream()
    screen = pyte.Screen(80, 24)
    screen.mode.discard(pyte.modes.LNM)
    stream.attach(screen)

    conn = telnetlib.Telnet("bs2.to")

    login(CONST['USER'], CONST['PASSWD'])
    term_comm('\x15', wait=True)

    position = CONST['BOARD']
    enterBoard(position)

    print '開始看魚'
    try:
        '''抓魚'''
        while True:
            scr = term_comm('s',wait=True)
            lines = scr.split("\n")
            checkNewFish(lines)
            checkCommand(CONST['USER'], CONST['MASTER'], lines)
    except KeyboardInterrupt:
        print '\n接收到 ^C 按鍵'
        logout()
    exit()
