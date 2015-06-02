package websocket

import (
	"fmt"
	"net/http"
	"testing"
)

type MyHandler struct {
}

func (wd MyHandler) CheckOrigin(origin, host string) bool {
	return true
}

func (wd MyHandler) OnOpen(ws *Websocket) {
	fmt.Println("OnOpen")
	ws.SendText([]byte("hello world from server"))
}

func (wd MyHandler) OnMessage(ws *Websocket, message []byte) {
	fmt.Println("OnMessage:", string(message), len(message))
}

func (wd MyHandler) OnClose(ws *Websocket, code uint16, reason []byte) {
	fmt.Println("OnClose", code, string(reason))
}

func (wd MyHandler) OnPong(ws *Websocket, data []byte) {
	fmt.Println("OnPong:", string(data))

}

func TestWebsocket(t *testing.T) {
	http.HandleFunc("/ws", func(w http.ResponseWriter, r *http.Request) {
		fmt.Println("...")
		var opt = Option{MyHandler{}, false}
		ws, err := New(w, r, &opt)
		if err != nil {
			t.Fatal(err.Error())
		}
		ws.Start()
	})
	fmt.Println("server start")
	http.ListenAndServe(":8001", nil)
}
