#include <stdio.h>
#include <stdlib.h>
#include <assert.h>

typedef int element;

struct Node {
    element ele;
    struct Node *next;
};

typedef struct Node *pNode;

pNode NewNode(element ele){
    pNode pnode = (pNode)malloc(sizeof(struct Node));
    pnode->ele = ele;
    pnode->next = NULL;
    return pnode;
}

void PrintNode(pNode pnode){
    assert(pnode != NULL);
    pNode p = pnode->next;
    while(p != NULL){
        printf("%d ", p->ele);
        p = p->next;
    }
}

pNode InsertNode(element ele){


}
