package websocket

import (
	"bufio"
	"bytes"
	"errors"
	"net"
	"net/http"
	"net/url"
)

var ()

//referer https://github.com/Skycrab/skynet_websocket/blob/master/websocket.lua

type WsHandler interface {
	CheckOrigin(origin, host string) bool
	OnOpen()
	OnMessage(message []byte)
	OnClose(code uint16, reason []byte)
	OnPong(data []byte)
}

type WsDefaultHandler struct {
	Ws            *Websocket
	CheckOriginOr bool // 是否校验origin, default true
}

func (wd *WsDefaultHandler) CheckOrigin(origin, host string) bool {

}

func (wd *WsDefaultHandler) OnOpen() {

}

func (wd *WsDefaultHandler) OnMessage(message []byte) bool {

}

func (wd *WsDefaultHandler) OnClose(code uint16, reason []byte) bool {

}

func (wd *WsDefaultHandler) OnPong(data []byte) bool {

}

type Websocket struct {
	net.Conn
	handler          WsHandler
	clientTerminated bool
	serverTerminated bool
	maskOutGoing     bool
}

/*
conf
    key       default-value

    "handler" WsDefaultHandler 默认处理器
    "maskoutgoing"   false     发送frame是否mask
*/

func New(W http.ResponseWriter, r *http.Request, conf map[string]interface{}) (*Websocket, error) {

	var h WsHandler
	if handler, ok := conf["handler"]; ok {
		h = handler.(WsHandler)
	} else {
		h = WsDefaultHandler{nil, true}
	}

	var maskOutGoing bool = false
	if mask, ok := conf["maskoutgong"]; ok {
		maskOutGoing = mask.(bool)
	}

	ws := new(Websocket)
	h.Ws = ws
	ws.Conn = w
	ws.handler = h
	ws.maskOutGoing = maskOutGoing

	return
}
