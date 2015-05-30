package murmur

import (
	"testing"
)

func TestMurmurHash2(t *testing.T) {
	var result uint32 = 403862830
	if result != DirectMurmurHash2([]byte("test")) {
		t.Error("DirectMurmurHash2 error")
	}
	mm := New()
	mm.Write([]byte("test"))
	code := mm.Sum32()
	mm.Reset()
	if result != code {
		t.Error("DirectMurmurHash2 error")
	}
}
