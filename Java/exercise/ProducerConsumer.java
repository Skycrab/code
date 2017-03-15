
import java.util.*;


class Factory{
    private LinkedList<Integer> goods;
    private static final int size=10;

    public Factory(){
        goods = new LinkedList<Integer>();
    }

    public synchronized int get(){
        while (goods.size() == 0){
            System.out.println("empty wait");
            try{
                wait();
            }catch (InterruptedException e){
                System.out.print(e);
                return 0;
            }
        }
        int g = goods.poll();
        notifyAll();
        return g;
    }

    public synchronized void put(int i) {
        while (goods.size() == Factory.size){
            System.out.println("full wait");
            try{
                wait();
            }catch (InterruptedException e){
                System.out.println(e);
            }
        }
        goods.add(i);
        notifyAll();
    }
}

class Producer implements Runnable{
    private Factory factory;

    public Producer(Factory factory){
        this.factory = factory;
    }

    @Override
    public void run() {
        for(int i=0;i<20;i++){
            factory.put(i);
            System.out.println("producer: "+i);
        }
    }
}

class Consumer implements Runnable{
    private Factory factory;

    public Consumer(Factory factory){
        this.factory = factory;
    }

    @Override
    public void run(){
        for(int i=0;i<20;i++){
            int g = factory.get();
            System.out.println("consumer: "+ g);
        }
    }
}

/**
 * Hello world!
 *
 */
public class ProducerConsumer
{
    public static void main( String[] args ) {

        Factory factory = new Factory();

        Producer producer = new Producer(factory);
        Consumer consumer = new Consumer(factory);

        Thread pp = new Thread(producer);
        Thread co = new Thread(consumer);

        pp.start();
        co.start();

    }
}

