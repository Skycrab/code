package progscala2

import scala.collection.generic.CanBuildFrom
import scala.collection.mutable

/**
  * 参考：https://juejin.im/post/597fe45f5188254ae52bbb19
  * https://scala.cool/2017/07/a-new-collection/
  * Created by skycrab on 18/9/5.
  */
object CanBuildFromTest {
  case class ListWrapper(list: List[Int])

  class B extends mutable.Builder[Int, ListWrapper] {
    var r = List[Int]()

    override def +=(elem: Int): B.this.type = {
      r ::= elem
      this
    }

    override def clear(): Unit = r = Nil

    override def result(): ListWrapper = ListWrapper(r)
  }


  class CBF extends CanBuildFrom[List[Int], Int, ListWrapper] {
    override def apply(from: List[Int]): mutable.Builder[Int, ListWrapper] = new B()

    override def apply(): mutable.Builder[Int, ListWrapper] = apply()
  }

  def main(args: Array[String]): Unit ={
    implicit val cbf = new CBF()
    val w = List(1,2,3).map[Int, ListWrapper](_*2)
    println(w)
  }

}
