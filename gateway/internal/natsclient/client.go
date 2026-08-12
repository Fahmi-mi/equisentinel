package natsclient

import (
	"errors"
	"time"

	"github.com/nats-io/nats.go"
)

type Client struct {
	nc *nats.Conn
	js nats.JetStreamContext
}

func Connect(url string) (*Client, error) {
	nc, err := nats.Connect(url)
	if err != nil {
		return nil, err
	}

	js, err := nc.JetStream()
	if err != nil {
		nc.Close()
		return nil, err
	}

	return &Client{nc: nc, js: js}, nil
}

func (c *Client) EnsureStream(name string, subjects []string, maxAge time.Duration) error {
	_, err := c.js.StreamInfo(name)
	if err == nil {
		return nil
	}
	if !errors.Is(err, nats.ErrStreamNotFound) {
		return err
	}

	_, err = c.js.AddStream(&nats.StreamConfig{
		Name:     name,
		Subjects: subjects,
		MaxAge:   maxAge,
	})
	return err
}

func (c *Client) JetStream() nats.JetStreamContext {
	return c.js
}

func (c *Client) IsConnected() bool {
	return c.nc != nil && c.nc.IsConnected()
}

func (c *Client) Close() {
	if c.nc != nil {
		c.nc.Drain()
	}
}
