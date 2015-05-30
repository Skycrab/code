package murmur

// MurmurHash2, by Austin Appleby

// Note - This code makes a few assumptions about how your machine behaves -

// 1. We can read a 4-byte value from any address without crashing
// 2. sizeof(int) == 4

// And it has a few limitations -

// 1. It will not work incrementally.
// 2. It will not produce the same results on little-endian and big-endian
//    machines.

import (
	"bytes"
	"encoding/binary"
)

const (
	murmur    uint32 = 0x5bd1e995
	Size             = 4
	BlockSize        = 4
)

type digest struct {
	hash  uint32
	rest  [4]byte
	first bool
	size  int
}

func New() *digest { return new(digest) }

func (d *digest) Reset() {
	d.hash = 0
	d.first = false
	d.size = 0
}

func (d *digest) Size() int { return Size }

func (d *digest) BlockSize() int { return BlockSize }

func (d *digest) Write(p []byte) (n int, err error) {
	var h uint32
	if !d.first {
		h = 0 ^ uint32(len(p))
		d.first = true
	} else {
		h = d.hash
	}
	h = d.hash ^ uint32(len(p))

	var np []byte

	if d.size == 0 {
		np = p
	} else {
		nn := d.size + len(p)
		np = make([]byte, nn)
		copy(np, d.rest[:d.size])
		copy(np[d.size:], p)
	}

	buf := bytes.NewBuffer(np)

	for buf.Len() >= 4 {
		var k uint32
		binary.Read(buf, binary.LittleEndian, &k)

		k *= murmur
		k ^= k >> 24
		k *= murmur

		h *= murmur
		h ^= k
	}

	if buf.Len() > 0 {
		d.size = copy(d.rest[:], buf.Bytes())
	} else {
		d.size = 0
	}

	d.hash = h

	return len(p), nil
}

func (d *digest) end() uint32 {
	h := d.hash
	if d.size != 0 {
		switch len(d.rest) {
		default:
			panic("not reachable")
		case 3:
			h ^= uint32(d.rest[2]) << 16
			fallthrough
		case 2:
			h ^= uint32(d.rest[1]) << 8
			fallthrough
		case 1:
			h ^= uint32(d.rest[0])
			h *= murmur
		case 0:
		}
	}

	h ^= h >> 13
	h *= murmur
	h ^= h >> 15

	d.hash = h
	return h
}

func (d *digest) Sum32() uint32 {
	h := d.end()
	return h
}

func (d *digest) Sum(in []byte) []byte {
	s := d.Sum32()
	return append(in, byte(s>>24), byte(s>>16), byte(s>>8), byte(s))
}

func Checksum(data []byte) uint32 {
	d := New()
	return d.Sum32()
}

//referer https://github.com/nginx/nginx/blob/master/src/core/ngx_murmurhash.c
func DirectMurmurHash2(data []byte) uint32 {
	buf := bytes.NewBuffer(data)
	h := 0 ^ uint32(len(data))
	for buf.Len() >= 4 {
		var k uint32
		binary.Read(buf, binary.LittleEndian, &k)

		k *= murmur
		k ^= k >> 24
		k *= murmur

		h *= murmur
		h ^= k
	}

	rest := buf.Bytes()
	switch len(rest) {
	default:
		panic("not reachable")
	case 3:
		h ^= uint32(rest[2]) << 16
		fallthrough
	case 2:
		h ^= uint32(rest[1]) << 8
		fallthrough
	case 1:
		h ^= uint32(rest[0])
		h *= murmur
	case 0:

	}

	h ^= h >> 13
	h *= murmur
	h ^= h >> 15
	return h
}
