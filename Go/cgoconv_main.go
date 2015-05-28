package main

/*
#include <stdio.h>
#include <stdlib.h>

typedef struct Man{
    int age;
    char **names;
}Man;

Man* create(){
    Man* m = (Man*)malloc(sizeof(Man));
    m->age = 24;
    m->names = (char**)malloc(sizeof(char*)*2);
    m->names[0]="GO";
    m->names[1]="C";
    return m;
}

void print(Man* m){
    int i=0;
    printf("age:%d\n",m->age);
    printf("names:");
    while(m->names[i]){
        printf("%d-%s  ",i,m->names[i]);
        i++;
    }
    printf("\n");
}
*/
import "C"

import (
	"fmt"
	"unsafe"
)

var PtrSize uintptr

func init() {
	var b *C.char
	PtrSize = unsafe.Sizeof(b)
}

//convert char** to []string
func CharStarStarSlice(src **C.char, size uintptr) []string {
	dst := make([]string, 0, size)
	i, begin := 0, uintptr(unsafe.Pointer(src))
	for {
		cur := (**C.char)(unsafe.Pointer(begin + uintptr(i)*PtrSize))
		p := (*C.char)(*cur)
		if p == nil {
			break
		}
		dst = append(dst, C.GoString(p))
		i++
	}
	return dst
}

func TestCharStarStarSlice() {
	m := C.create()
	names := CharStarStarSlice(m.names, 2)
	fmt.Println("age:", m.age)
	fmt.Println("names:", names)
}

func main() {
	TestCharStarStarSlice()
}
